"""
Backup scheduler module for managing automated backup schedules.
"""

import time
from pathlib import Path
from typing import Dict, Optional
import schedule

from .base import S3BaseHandler, S3BaseError


class BackupSchedulerError(S3BaseError):
    """Custom exception for backup scheduler operations."""


class BackupScheduler(S3BaseHandler):
    """Handles scheduled backup operations to AWS S3."""

    def __init__(
        self,
        bucket_name: str,
        aws_region: str = "us-east-1",
        backup_prefix: str = "automated_backup",
    ) -> None:
        """Initialize the backup scheduler."""
        super().__init__(bucket_name, aws_region, backup_prefix)
        self.scheduler = schedule.Scheduler()
        self.jobs = {}

    def schedule_backup(
        self,
        file_path: Path,
        schedule_type: str,
        interval: int,
        retention_days: Optional[int] = 30,
    ) -> str:
        """Schedule a backup job."""
        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        if schedule_type not in ["minutes", "hours", "days"]:
            raise ValueError(f"Invalid schedule type: {schedule_type}")

        job_id = f"{file_path}_{time.time()}"
        schedule_func = getattr(self.scheduler.every(interval), schedule_type)
        job = schedule_func.do(self._perform_backup, file_path, retention_days)
        self.jobs[job_id] = job

        return job_id

    def _perform_backup(self, file_path: Path, retention_days: int) -> Dict[str, str]:
        """Perform the actual backup operation."""
        try:
            with open(file_path, "rb") as file:
                s3_key = f"{self.backup_prefix}/{file_path.name}_{int(time.time())}"
                response = self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=file,
                    Metadata={
                        "retention_days": str(retention_days),
                        "original_path": str(file_path),
                    },
                )

            return {
                "bucket": self.bucket_name,
                "key": s3_key,
                "version_id": response.get("VersionId", "None"),
            }

        except Exception as error:
            self.logger.error(
                "Scheduled backup failed for %s: %s", file_path, str(error)
            )
            raise BackupSchedulerError(
                f"Scheduled backup failed: {str(error)}"
            ) from error

    def start(self) -> None:
        """Start the scheduler."""
        while True:
            self.scheduler.run_pending()
            time.sleep(1)

    def stop(self) -> None:
        """Stop all scheduled jobs."""
        self.scheduler.clear()
        self.jobs.clear()
