"""
Backup scheduler module for managing automated backup jobs.
Provides scheduling and execution of backup tasks.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class BackupJob:
    """Represents a scheduled backup job with timing and location details."""
    name: str
    frequency: timedelta
    source_path: str
    destination_bucket: str
    next_run: datetime
    last_run: Optional[datetime] = None

class BackupScheduler:
    """
    A class to manage scheduled backup jobs.
    """
    def __init__(self):
        """Initialize the BackupScheduler with an empty job list."""
        self.jobs: List[BackupJob] = []
    
    def add_job(self, job: BackupJob) -> None:
        """
        Add a new backup job to the scheduler.

        Args:
            job: BackupJob instance to be scheduled
        """
        self.jobs.append(job)