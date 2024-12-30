import pytest
from pathlib import Path
from ..log_reader import LogReader

def test_read_nonexistent_file():
    """Test that reading a nonexistent file returns an empty list."""
    reader = LogReader("nonexistent_file.log")
    result = reader.read_log()
    assert result == [], "Reading nonexistent file should return empty list"

def test_read_existing_file(tmp_path):
    """Test reading a file with known content."""
    # Create a temporary log file
    log_file = tmp_path / "test.log"
    test_content = ["line 1\n", "line 2\n"]
    log_file.write_text("".join(test_content))
    
    # Read and verify the content
    reader = LogReader(str(log_file))
    result = reader.read_log()
    assert result == test_content, "File content should match what was written"