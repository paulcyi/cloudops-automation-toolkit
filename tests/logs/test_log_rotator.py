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


def test_rotation_size_check(test_log_file):
    """Test log rotation size threshold check."""
    # Create an empty file first
    test_log_file.write_text("")
    rotator = LogRotator(test_log_file, max_size_bytes=10)
    
    # File should be smaller than threshold initially
    assert not rotator.should_rotate()
    
    # Add content to exceed threshold
    test_log_file.write_text("Content that exceeds threshold")
    assert rotator.should_rotate()


def test_log_rotation_execution(test_log_file):
    """Test actual log file rotation."""
    content = "Test log content"
    test_log_file.write_text(content)
    
    rotator = LogRotator(test_log_file, max_size_bytes=10)
    rotator.rotate()
    
    # Check that backup file exists
    backup_files = list(test_log_file.parent.glob("*.log.*"))
    assert len(backup_files) == 1
    
    # Check that original file is empty
    assert test_log_file.read_text() == ""


def test_max_files_cleanup(test_log_file):
    """Test cleanup of old log files."""
    max_files = 2
    rotator = LogRotator(test_log_file, max_size_bytes=10, max_files=max_files)
    
    # Create multiple rotations
    for i in range(4):
        test_log_file.write_text(f"Content {i}" * 10)
        time.sleep(0.1)  # Ensure unique timestamps
        rotator.rotate()
    
    # Check file count
    log_files = list(test_log_file.parent.glob("test.log*"))
    assert len(log_files) == max_files + 1  # max_files backups + current