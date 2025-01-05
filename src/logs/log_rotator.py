"""Log rotation module for managing log file sizes and retention."""

from pathlib import Path
import shutil
import logging
from datetime import datetime
from typing import Optional

class LogRotator:
    def __init__(
        self,
        log_path: Path,
        max_size_bytes: int = 10_485_760,  # 10MB default
        max_files: int = 5,
        retention_days: Optional[int] = 30
    ):
        self.log_path = Path(log_path)
        self.max_size_bytes = max_size_bytes
        self.max_files = max_files
        self.retention_days = retention_days
        
        self.logger = logging.getLogger(__name__)
    
    def should_rotate(self) -> bool:
        """Check if log file should be rotated based on size."""
        if not self.log_path.exists():
            return False
        return self.log_path.stat().st_size >= self.max_size_bytes
    
    def rotate(self) -> bool:
        """Rotate log file if needed."""
        try:
            if not self.should_rotate():
                return False
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.log_path.with_suffix(f".{timestamp}.log")
            
            # Rotate the file
            shutil.copy2(self.log_path, backup_path)
            self.log_path.write_text("")  # Clear original file
            
            # Cleanup old files if needed
            self._cleanup_old_logs()
            
            self.logger.info(f"Rotated log file to {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rotate log: {str(e)}")
            return False
    
    def _cleanup_old_logs(self) -> None:
        """Remove old log files based on retention policy."""
        log_files = sorted(
            self.log_path.parent.glob(f"{self.log_path.stem}.*{self.log_path.suffix}"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        # Remove files exceeding max_files
        for file in log_files[self.max_files:]:
            file.unlink()
            self.logger.info(f"Removed old log file: {file}")