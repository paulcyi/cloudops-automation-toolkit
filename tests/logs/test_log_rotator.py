import pytest
from pathlib import Path
from datetime import datetime
from src.logs.log_rotator import LogRotator

@pytest.fixture
def test_log_file(tmp_path):
    """Create a temporary log file for testing."""
    log_file = tmp_path / "test.log"
    log_file.write_text("Initial log content\n")
    return log_file

def test_rotation_size_check(test_log_file):
    """Test log rotation size threshold check."""
    rotator = LogRotator(test_log_file, max_size_bytes=10)
    
    # File should be smaller than threshold initially
    assert not rotator.should_rotate()
    
    # Add content to exceed threshold
    test_log_file.write_text("A" * 20)
    assert rotator.should_rotate()

def test_log_rotation_execution(test_log_file):
    """Test actual log rotation process."""
    rotator = LogRotator(test_log_file, max_size_bytes=10)
    
    # Add content to trigger rotation
    test_log_file.write_text("A" * 20)
    
    # Perform rotation
    assert rotator.rotate()
    
    # Check results
    rotated_files = list(test_log_file.parent.glob("*.log"))
    assert len(rotated_files) == 2  # Original + backup
    assert test_log_file.read_text() == ""  # Original should be empty

def test_max_files_cleanup(test_log_file):
    """Test cleanup of old log files."""
    max_files = 2
    rotator = LogRotator(test_log_file, max_size_bytes=10, max_files=max_files)
    
    # Create multiple rotations
    for i in range(4):
        test_log_file.write_text(f"Content {i}" * 10)
        rotator.rotate()
    
    # Check file count
    log_files = list(test_log_file.parent.glob("*.log"))
    assert len(log_files) == max_files + 1  # max_files backups + current