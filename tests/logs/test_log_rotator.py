"""Test suite for the log rotator module."""

import time
from pathlib import Path
import pytest
from src.logs.log_rotator import LogRotator


@pytest.fixture
def test_log_file(tmp_path) -> Path:
    """Create a test log file."""
    log_file = tmp_path / "test.log"
    log_file.write_text("Initial log content")
    return log_file


def test_max_files_cleanup(test_log_file):
    """Test cleanup of old log files."""
    max_files = 2
    rotator = LogRotator(test_log_file, max_size_bytes=10, max_files=max_files)

    # Create multiple rotations with guaranteed unique content and timestamps
    for i in range(4):
        # Write unique content
        test_log_file.write_text(f"Content {i}" * 20)  # Make content longer
        rotator.rotate()
        time.sleep(0.1)  # Ensure unique timestamps

    # Get all log files
    log_files = sorted(
        test_log_file.parent.glob("test.log*"), key=lambda x: x.stat().st_mtime
    )

    # Verify file count (max_files backups + current log file)
    assert (
        len(log_files) == max_files + 1
    ), f"Expected {max_files + 1} files, got {len(log_files)}: {[f.name for f in log_files]}"

    # Verify current log file exists and is empty
    assert test_log_file.exists()
    assert test_log_file.stat().st_size == 0

    # Verify backup files exist and have content
    backup_files = [f for f in log_files if f != test_log_file]
    assert len(backup_files) == max_files

    # Verify all backup files are unique
    backup_timestamps = [f.name.split(".")[-1] for f in backup_files]
    assert len(set(backup_timestamps)) == len(
        backup_timestamps
    ), "Backup files should have unique timestamps"
