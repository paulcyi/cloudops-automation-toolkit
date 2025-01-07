import pytest
from pathlib import Path
from src.logs.log_reader import LogReader

def test_read_nonexistent_file():
    """Test that reading a nonexistent file returns an empty list."""
    reader = LogReader("nonexistent_file.log")
    result = reader.read_log()
    assert result == [], "Reading nonexistent file should return empty list"

def test_read_existing_file(tmp_path):
    """Test reading a file with known content."""
    log_file = tmp_path / "test.log"
    test_content = ["line 1\n", "line 2\n"]
    log_file.write_text("".join(test_content))
    
    reader = LogReader(str(log_file))
    result = reader.read_log()
    assert result == test_content, "File content should match what was written"

def test_find_patterns(tmp_path):
    """Test pattern matching in log files."""
    log_file = tmp_path / "test.log"
    test_content = [
        "2024-12-30 10:15:30 ERROR Database connection failed\n",
        "2024-12-30 10:15:35 INFO Normal operation resumed\n",
        "2024-12-30 10:15:40 ERROR Network timeout\n"
    ]
    log_file.write_text("".join(test_content))
    
    reader = LogReader(str(log_file))
    
    # Test finding ERROR patterns
    error_matches = reader.find_patterns(r'ERROR.*')
    assert len(error_matches) == 2, "Should find two ERROR entries"
    assert all('ERROR' in match['pattern_match'] for match in error_matches)
    assert all('2024-12-30' in match['timestamp'] for match in error_matches)

    # Test finding INFO patterns
    info_matches = reader.find_patterns(r'INFO.*')
    assert len(info_matches) == 1, "Should find one INFO entry"
    assert 'INFO' in info_matches[0]['pattern_match']

def test_error_pattern_matching(tmp_path):
    """Test finding error patterns in logs."""
    # Create a test log file
    log_file = tmp_path / "errors.log"
    test_content = [
        "2024-12-30 23:15:00 INFO: Application started\n",
        "2024-12-30 23:16:00 ERROR: Database connection failed\n",
        "2024-12-30 23:17:00 INFO: Retry connection\n"
    ]
    log_file.write_text("".join(test_content))
    
    # Use LogReader to find ERROR patterns
    reader = LogReader(str(log_file))
    error_matches = reader.find_patterns(r'ERROR.*')
    
    # Verify we found the error
    assert len(error_matches) == 1, "Should find one error"
    assert "Database connection failed" in error_matches[0]['content']
    assert error_matches[0]['timestamp'] == "2024-12-30 23:16:00"