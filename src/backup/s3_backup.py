"""
S3 backup module for managing automated backups to AWS S3.

This module provides comprehensive backup management capabilities including
creation, verification, restoration, and metadata management for AWS S3 backups.
"""

# Standard library imports
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

# Third-party imports
import boto3
from botocore.exceptions import ClientError


class S3BackupError(Exception):
    """Custom exception for S3 backup operations."""


class S3ConnectionError(S3BackupError):
    """Exception raised for S3 connection and authentication issues."""


class S3OperationError(S3BackupError):
    """Exception raised for S3 operation failures."""


class S3BackupHandler:
    """
    Handles automated backups to AWS S3 with verification and restoration capabilities.

    This class provides a comprehensive interface for managing backups in AWS S3,
    including backup creation, verification, listing, and restoration.

    Attributes:
        bucket_name (str): Name of the S3 bucket for backups
        backup_prefix (str): Prefix for backup objects in S3
        logger (logging.Logger): Logger instance for the class
    """

    def __init__(
        self,
        bucket_name: str,
        aws_region: str = "us-east-1",
        backup_prefix: str = "automated_backup",
    ) -> None:
        """
        Initialize the S3BackupHandler.

        Args:
            bucket_name: Name of the S3 bucket for backups
            aws_region: AWS region for the S3 bucket (default: "us-east-1")
            backup_prefix: Prefix for backup objects in S3 (default: "automated_backup")

        Raises:
            S3ConnectionError: If initialization or bucket access fails
        """
        self.bucket_name = bucket_name
        self.backup_prefix = backup_prefix
        self.logger = logging.getLogger(__name__)

        try:
            self.s3_client = boto3.client("s3", region_name=aws_region)
            self._verify_bucket_access()
        except Exception as error:
            self.logger.error("Failed to initialize S3 client: %s", str(error))
            raise S3ConnectionError(
                f"S3 client initialization failed: {str(error)}"
            ) from error

    def _verify_bucket_access(self) -> None:
        """
        Verify access to the S3 bucket.

        Raises:
            S3ConnectionError: If bucket access fails
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as error:
            error_code = error.response.get("Error", {}).get("Code", "Unknown")
            error_mapping = {
                "404": f"Bucket {self.bucket_name} does not exist",
                "403": f"Access denied to bucket {self.bucket_name}",
            }
            msg = error_mapping.get(
                error_code, f"Error accessing bucket {self.bucket_name}: {error_code}"
            )
            self.logger.error(msg)
            raise S3ConnectionError(msg) from error

    def _generate_backup_key(self, file_path: Path) -> str:
        """
        Generate a unique backup key for S3 object.

        Args:
            file_path: Path to the file being backed up

        Returns:
            str: Generated S3 key for the backup
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.backup_prefix}/{file_path.name}_{timestamp}"

    def create_backup(
        self, file_path: Path, retention_days: Optional[int] = 30
    ) -> Dict[str, str]:
        """
        Create a backup of the specified file in S3.

        Args:
            file_path: Path to the file to backup
            retention_days: Number of days to retain the backup (default: 30)

        Returns:
            Dict[str, str]: Dictionary containing backup details (bucket, key, version)

        Raises:
            S3OperationError: If backup creation fails
            FileNotFoundError: If source file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        try:
            s3_key = self._generate_backup_key(file_path)
            metadata = {
                "retention_days": str(retention_days),
                "original_path": str(file_path),
                "backup_date": datetime.now().strftime("%Y%m%d_%H%M%S"),
            }

            with open(file_path, "rb") as file:
                response = self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=file,
                    Metadata=metadata,
                )

            self.logger.info("Successfully created backup: %s", s3_key)
            return {
                "bucket": self.bucket_name,
                "key": s3_key,
                "version_id": response.get("VersionId", "None"),
            }

        except Exception as error:
            self.logger.error(
                "Failed to create backup for %s: %s", file_path, str(error)
            )
            raise S3OperationError(f"Backup creation failed: {str(error)}") from error

    def verify_backup(self, backup_info: Dict[str, str]) -> bool:
        """
        Verify the integrity of a backup in S3.

        Args:
            backup_info: Dictionary containing backup details

        Returns:
            bool: True if backup is valid, False otherwise

        Raises:
            S3OperationError: If verification check fails
        """
        try:
            self.s3_client.head_object(
                Bucket=backup_info["bucket"],
                Key=backup_info["key"],
            )
            return True
        except ClientError as error:
            self.logger.error("Failed to verify backup: %s", str(error))
            return False
        except Exception as error:
            raise S3OperationError(
                f"Backup verification failed: {str(error)}"
            ) from error

    def _get_object_metadata(self, key: str) -> Dict[str, str]:
        """
        Retrieve metadata for an S3 object.

        Args:
            key: S3 object key

        Returns:
            Dict[str, str]: Object metadata or empty dict if metadata fetch fails
        """
        try:
            metadata = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return metadata.get("Metadata", {})
        except ClientError as error:
            self.logger.warning("Failed to fetch metadata for %s: %s", key, str(error))
            return {}

    def list_backups(self, max_items: int = 100) -> List[Dict[str, Union[str, int]]]:
        """
        List available backups in S3.

        Args:
            max_items: Maximum number of backups to list (default: 100)

        Returns:
            List[Dict[str, Union[str, int]]]: List of backup details

        Raises:
            S3OperationError: If listing backups fails
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.backup_prefix,
                MaxKeys=max_items,
            )

            backups = []
            for obj in response.get("Contents", []):
                backup_info = {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                }
                backup_info["metadata"] = self._get_object_metadata(obj["Key"])
                backups.append(backup_info)

            return backups

        except ClientError as error:
            self.logger.error("Failed to list backups: %s", str(error))
            raise S3OperationError(f"Failed to list backups: {str(error)}") from error

    def restore_backup(
        self, backup_key: str, destination_path: Path, overwrite: bool = False
    ) -> bool:
        """
        Restore a backup from S3.

        Args:
            backup_key: S3 key of the backup to restore
            destination_path: Path where to restore the backup
            overwrite: Whether to overwrite existing files (default: False)

        Returns:
            bool: True if restoration was successful

        Raises:
            S3OperationError: If restoration fails
            FileExistsError: If destination exists and overwrite is False
        """
        if destination_path.exists() and not overwrite:
            raise FileExistsError(
                f"Destination path {destination_path} exists and overwrite is False"
            )

        try:
            with open(destination_path, "wb") as file:
                self.s3_client.download_fileobj(
                    self.bucket_name,
                    backup_key,
                    file,
                )

            self.logger.info(
                "Successfully restored backup %s to %s",
                backup_key,
                destination_path,
            )
            return True

        except Exception as error:
            self.logger.error("Failed to restore backup %s: %s", backup_key, str(error))
            raise S3OperationError(
                f"Backup restoration failed: {str(error)}"
            ) from error
