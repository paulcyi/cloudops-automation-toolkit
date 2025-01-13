"""
Backup scheduler module for managing automated backup schedules.
"""

import time
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
import schedule

from botocore.exceptions import ClientError
from .base import S3BaseHandler, S3BaseError


class BackupSchedulerError(S3BaseError):
    """Custom exception for backup scheduler operations."""


class BackupVerificationError(BackupSchedulerError):
    """Custom exception for backup verification failures."""


class BackupMetadataError(BackupSchedulerError):
    """Custom exception for metadata validation failures."""


@dataclass
class BackupConfig:
    """Configuration for backup operations."""

    aws_region: str = "us-east-1"
    backup_prefix: str = "automated_backup"
    max_retries: int = 3
    min_retention_days: int = 1
    max_retention_days: int = 365


@dataclass
class BackupMetadata:
    """Data class for backup metadata validation and tracking."""

    file_path: str
    backup_date: str
    retention_days: int
    sha256_hash: str
    size_bytes: int
    status: str = "pending"  # pending, success, failed

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "BackupMetadata":
        """Create BackupMetadata instance from dictionary."""
        return cls(
            file_path=data["original_path"],
            backup_date=data["backup_date"],
            retention_days=int(data["retention_days"]),
            sha256_hash=data["sha256_hash"],
            size_bytes=int(data.get("size_bytes", 0)),
            status=data.get("status", "pending"),
        )


class BackupScheduler(S3BaseHandler):
    """Handles scheduled backup operations to AWS S3."""

    def __init__(
        self,
        bucket_name: str,
        config: Optional[BackupConfig] = None,
    ) -> None:
        """Initialize the backup scheduler.

        Args:
            bucket_name: Name of the S3 bucket
            config: Optional backup configuration
        """
        self.config = config or BackupConfig()
        super().__init__(bucket_name, self.config.aws_region, self.config.backup_prefix)
        self.scheduler = schedule.Scheduler()
        self.jobs = {}
        self.metadata_history: List[BackupMetadata] = []
        self.max_retries = self.config.max_retries
        self.min_retention_days = self.config.min_retention_days
        self.max_retention_days = self.config.max_retention_days

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA-256 hash of the file

        Raises:
            OSError: If file reading fails
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except OSError as e:
            self.logger.error("Failed to calculate hash for %s: %s", file_path, e)
            raise

    def _verify_backup(self, file_path: Path, s3_key: str) -> bool:
        """Verify the integrity of a backup by comparing file hashes.

        Args:
            file_path: Path to the original file
            s3_key: S3 key of the backup

        Returns:
            bool indicating if verification passed

        Raises:
            BackupVerificationError: If verification fails
        """
        try:
            # Calculate local file hash
            local_hash = self._calculate_file_hash(file_path)

            # Get S3 object metadata containing the original hash
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            s3_hash = response.get("Metadata", {}).get("sha256_hash")

            if not s3_hash:
                raise BackupVerificationError(f"No hash found in metadata for {s3_key}")

            # Compare hashes
            if local_hash != s3_hash:
                self.logger.error(
                    "Hash mismatch - Local: %s, S3: %s", local_hash, s3_hash
                )
                return False

            self.logger.info("Backup verification successful for %s", s3_key)
            return True

        except (OSError, ClientError) as e:
            self.logger.error("Backup verification failed: %s", str(e))
            raise BackupVerificationError(
                f"Backup verification failed: {str(e)}"
            ) from e

    def _validate_metadata(self, metadata: Dict[str, str]) -> BackupMetadata:
        """Validate backup metadata.

        Args:
            metadata: Dictionary containing backup metadata

        Returns:
            BackupMetadata: Validated metadata object

        Raises:
            BackupMetadataError: If metadata validation fails
        """
        required_fields = {
            "original_path",
            "backup_date",
            "retention_days",
            "sha256_hash",
        }

        missing_fields = required_fields - set(metadata.keys())
        if missing_fields:
            raise BackupMetadataError(
                f"Missing required metadata fields: {missing_fields}"
            )

        try:
            retention_days = int(metadata["retention_days"])
            if not self.min_retention_days <= retention_days <= self.max_retention_days:
                raise BackupMetadataError(
                    f"Retention days must be between {self.min_retention_days} "
                    f"and {self.max_retention_days}"
                )

            # Validate backup date format
            datetime.fromisoformat(metadata["backup_date"])

            # Validate hash format
            if not re.match(r"^[a-fA-F0-9]{64}$", metadata["sha256_hash"]):
                raise BackupMetadataError("Invalid SHA-256 hash format")

            return BackupMetadata.from_dict(metadata)

        except (ValueError, TypeError) as e:
            raise BackupMetadataError(f"Metadata validation failed: {str(e)}") from e

    def _update_metadata_history(self, metadata: BackupMetadata) -> None:
        """Update backup metadata history.

        Args:
            metadata: BackupMetadata object to add to history
        """
        self.metadata_history.append(metadata)
        while len(self.metadata_history) > 1000:  # Keep last 1000 entries
            self.metadata_history.pop(0)

    def _perform_backup(self, file_path: Path, retention_days: int) -> Dict[str, str]:
        """Perform the actual backup operation with verification.

        Args:
            file_path: Path to the file to backup
            retention_days: Number of days to retain the backup

        Returns:
            Dict containing backup details

        Raises:
            BackupSchedulerError: If backup or verification fails
            OSError: If file operations fail
            ClientError: If S3 operations fail
        """
        retries = 0
        while retries < self.max_retries:
            try:
                # Calculate file hash before upload
                file_hash = self._calculate_file_hash(file_path)

                # Prepare metadata
                metadata = {
                    "retention_days": str(retention_days),
                    "original_path": str(file_path),
                    "sha256_hash": file_hash,
                    "backup_date": datetime.now().isoformat(),
                }

                # Perform backup
                with open(file_path, "rb") as file:
                    s3_key = f"{self.backup_prefix}/{file_path.name}_{int(time.time())}"
                    response = self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=s3_key,
                        Body=file,
                        Metadata=metadata,
                    )

                # Verify backup
                if self._verify_backup(file_path, s3_key):
                    return {
                        "bucket": self.bucket_name,
                        "key": s3_key,
                        "version_id": response.get("VersionId", "None"),
                        "hash": file_hash,
                    }

                # If verification fails, retry
                self.logger.warning(
                    "Backup verification failed, attempt %d of %d",
                    retries + 1,
                    self.max_retries,
                )
                retries += 1

            except (OSError, ClientError) as e:
                self.logger.error(
                    "Backup attempt %d failed for %s: %s",
                    retries + 1,
                    file_path,
                    str(e),
                )
                retries += 1
                if retries >= self.max_retries:
                    raise BackupSchedulerError(
                        f"Backup failed after {self.max_retries} attempts: {str(e)}"
                    ) from e

                time.sleep(2**retries)  # Exponential backoff

        raise BackupSchedulerError(f"Backup failed after {self.max_retries} attempts")

    def get_backup_statistics(self) -> Dict[str, float]:
        """Calculate statistics about backups."""
        if not self.metadata_history:
            return {
                "success_rate": 0.0,
                "total_backups": 0,
                "average_size_mb": 0.0,
            }

        total_backups = len(self.metadata_history)
        successful_backups = sum(1 for metadata in self.metadata_history if metadata.status == "success")
        total_size_bytes = sum(metadata.size_bytes for metadata in self.metadata_history)

        success_rate = (successful_backups / total_backups) * 100 if total_backups > 0 else 0
        average_size_mb = (total_size_bytes / total_backups) / (1024 * 1024) if total_backups > 0 else 0

        return {
            "success_rate": success_rate,
            "total_backups": total_backups,
            "average_size_mb": average_size_mb,
        }

    def schedule_backup(
        self,
        file_path: Path,
        schedule_type: str,
        interval: int,
        retention_days: Optional[int] = 30,
    ) -> str:
        """Schedule a backup job.

        Args:
            file_path: Path to the file to backup
            schedule_type: Type of schedule (minutes, hours, days)
            interval: Interval for the schedule
            retention_days: Number of days to retain the backup (default: 30)

        Returns:
            str: Job ID for the scheduled backup

        Raises:
            FileNotFoundError: If source file doesn't exist
            ValueError: If schedule type is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        if schedule_type not in ["minutes", "hours", "days"]:
            raise ValueError(f"Invalid schedule type: {schedule_type}")

        job_id = f"{file_path}_{time.time()}"
        schedule_func = getattr(self.scheduler.every(interval), schedule_type)
        job = schedule_func.do(self._perform_backup, file_path, retention_days)
        self.jobs[job_id] = job

        return job_id
