"""Test suite for the backup scheduler module."""

import pytest
from datetime import datetime, timedelta
from src.backup.scheduler import BackupScheduler, BackupJob

@pytest.fixture
def scheduler():
    """Fixture to create a fresh BackupScheduler instance for each test."""
    return BackupScheduler()

def test_scheduler_initialization(scheduler):
    """Test that BackupScheduler initializes correctly."""
    assert scheduler is not None
    assert len(scheduler.jobs) == 0

def test_add_backup_job(scheduler):
    """Test adding a new backup job to the scheduler."""
    # Create a backup job for testing
    job = BackupJob(
        name="test-backup",
        frequency=timedelta(hours=24),
        source_path="/test/source",
        destination_bucket="test-bucket",
        next_run=datetime.now()
    )
    
    scheduler.add_job(job)
    assert len(scheduler.jobs) == 1
    assert scheduler.jobs[0].name == "test-backup"