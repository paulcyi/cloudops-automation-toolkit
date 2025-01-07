"""
Log rotation module for managing log file sizes and retention.
"""

from pathlib import Path
from datetime import datetime
import logging
import shutil
import os

class LogRotator:
    """Handles log file rotation based on size and count limits."""

    def __init__(
        self,
        log_file: Path,
        max_size_bytes: int = 1024 * 1024,
        max_files: int = 5,
    ):
        self.log_file = log_file
        self.max_size_bytes = max_size_bytes
        self.max_files = max_files
        self.logger = logging.getLogger(__name__)

    def should_rotate(self) -> bool:
        """Check if log file should be rotated based on size."""
        if not self.log_file.exists():
            return False
        try:
            return self.log_file.stat().st_size > self.max_size_bytes
        except FileNotFoundError:
            return False

    def rotate(self) -> None:
        """Rotate the log file and manage backups."""
        if not self.should_rotate():
            return

        # Run cleanup before creating new backup
        self.cleanup_old_files()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_file = self.log_file.with_name(
            f"{self.log_file.stem}{self.log_file.suffix}.{timestamp}"
        )

        try:
            shutil.copy2(self.log_file, rotated_file)
            with open(self.log_file, 'w') as f:
                f.truncate(0)
            self.logger.info(f"Rotated log file to {rotated_file}")
        except Exception as e:
            self.logger.error(f"Failed to rotate log file: {e}")
            raise

    def cleanup_old_files(self) -> None:
        """Remove oldest log files when max_files limit is exceeded."""
        # Get all backup files, sorted by modification time (newest first)
        backup_files = sorted(
            [f for f in self.log_file.parent.glob(f"{self.log_file.stem}{self.log_file.suffix}.*")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        # Keep only max_files - 1 backup files
        files_to_remove = backup_files[self.max_files - 1:]
        for old_file in files_to_remove:
            try:
                old_file.unlink()
                self.logger.info(f"Removed old log file: {old_file}")
            except Exception as e:
                self.logger.error(f"Failed to remove old log file {old_file}: {e}")