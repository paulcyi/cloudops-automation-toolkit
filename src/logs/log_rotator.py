"""
Log rotation module for managing log file sizes and retention.
"""

from pathlib import Path
from datetime import datetime
import logging
import shutil
import os
import time


class LogRotator:
    """Handles log file rotation based on size and count limits."""

    def __init__(
        self,
        log_file: Path,
        max_size_bytes: int = 1024 * 1024,  # 1MB default
        max_files: int = 5,
    ):
        """Initialize LogRotator with file path and limits.

        Args:
            log_file: Path to the log file to manage
            max_size_bytes: Maximum size in bytes before rotation
            max_files: Maximum number of backup files to keep
        """
        self.log_file = log_file
        self.max_size_bytes = max_size_bytes
        self.max_files = max_files
        self.logger = logging.getLogger(__name__)

    def should_rotate(self) -> bool:
        """Check if log file should be rotated based on size.

        Returns:
            bool: True if file exceeds size limit, False otherwise
        """
        if not self.log_file.exists():
            return False
        try:
            return self.log_file.stat().st_size > self.max_size_bytes
        except FileNotFoundError:
            return False

    def rotate(self) -> None:
        """Rotate the log file and manage backups.

        Raises:
            OSError: If file operations fail
        """
        if not self.should_rotate():
            return

        # Generate unique timestamp with microseconds and counter
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        # Add a small sleep to ensure unique timestamps in rapid succession
        time.sleep(0.01)

        rotated_file = self.log_file.with_name(
            f"{self.log_file.stem}{self.log_file.suffix}.{timestamp}"
        )

        try:
            # Copy current log to backup
            shutil.copy2(self.log_file, rotated_file)
            # Truncate current log
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.truncate(0)
            self.logger.info("Rotated log file to %s", rotated_file)

            # Run cleanup after successful rotation
            self.cleanup_old_files()

        except OSError as e:
            self.logger.error("Failed to rotate log file: %s", e)
            raise

    def cleanup_old_files(self) -> None:
        """Remove oldest log files when max_files limit is exceeded.

        Raises:
            OSError: If file deletion fails
        """
        try:
            # Get all backup files, sorted by modification time (oldest first)
            pattern = f"{self.log_file.stem}{self.log_file.suffix}.*"
            backup_files = sorted(
                self.log_file.parent.glob(pattern), key=lambda x: x.stat().st_mtime
            )

            # If we have more than max_files backups, remove oldest ones
            files_to_remove = (
                backup_files[: -self.max_files]
                if len(backup_files) > self.max_files
                else []
            )

            for old_file in files_to_remove:
                try:
                    old_file.unlink()
                    self.logger.info("Removed old log file: %s", old_file)
                except OSError as e:
                    self.logger.error(
                        "Failed to remove old log file %s: %s", old_file, e
                    )
                    raise

        except OSError as e:
            self.logger.error("Failed during cleanup: %s", e)
            raise
