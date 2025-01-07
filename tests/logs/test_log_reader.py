"""Test suite for the log reader module."""

from datetime import datetime
from pathlib import Path
import pytest
from src.logs.log_reader import LogReader


@pytest.fixture
def test_log_file(tmp_path) -> Path:
    """Create a test log file with sample content."""
    log_file = tmp_path / "test.log"
    test_content = [
        "2024-12-30 10:15:30 ERROR Database connection failed\n",
        "2024-12-30 10:15:35 INFO Normal operation resumed\n",
        "2024-12-30 10:15:40 ERROR Network timeout\n",
    ]
    log_file.write_text("".join(test_content))
    return log_file


def test_read_nonexistent_file():
    """Test that reading a nonexistent file returns an empty list."""
    reader = LogReader("nonexistent_file.log")
    result = reader.read_log()
    assert result == [], "Reading nonexistent file should return empty list"


def test_read_existing_file(test_log_file):
    """Test reading a file with known content."""
    reader = LogReader(str(test_log_file))
    result = reader.read_log()
    assert len(result) == 3, "Should read all lines from file"
    assert "ERROR Database connection failed" in result[0]


def test_find_patterns(test_log_file):
    """Test pattern matching in log files."""
    reader = LogReader(str(test_log_file))

    # Test finding ERROR patterns
    error_matches = reader.find_patterns(r"ERROR.*")
    assert len(error_matches) == 2, "Should find two ERROR entries"
    assert all("ERROR" in match["pattern_match"] for match in error_matches)
    assert all("2024-12-30" in match["timestamp"] for match in error_matches)

    # Test finding INFO patterns
    info_matches = reader.find_patterns(r"INFO.*")
    assert len(info_matches) == 1, "Should find one INFO entry"
    assert "INFO" in info_matches[0]["pattern_match"]


def test_invalid_pattern(test_log_file):
    """Test handling of invalid regex patterns."""
    reader = LogReader(str(test_log_file))
    with pytest.raises(ValueError, match="Invalid regular expression pattern"):
        reader.find_patterns(r"[invalid")


def test_find_patterns_in_timerange(test_log_file):
    """Test finding patterns within a specific time range."""
    reader = LogReader(str(test_log_file))

    start_time = datetime(2024, 12, 30, 10, 15, 30)
    end_time = datetime(2024, 12, 30, 10, 15, 35)

    matches = reader.find_patterns_in_timerange(r".*", start_time, end_time)
    assert len(matches) == 2, "Should find entries within time range"


def test_invalid_timerange(test_log_file):
    """Test handling of invalid time ranges."""
    reader = LogReader(str(test_log_file))

    end_time = datetime(2024, 12, 30, 10, 15, 30)
    start_time = datetime(2024, 12, 30, 10, 15, 35)

    with pytest.raises(ValueError, match="Start time must be before end time"):
        reader.find_patterns_in_timerange(r".*", start_time, end_time)


def test_file_read_error(tmp_path):
    """Test handling of file read errors."""
    log_file = tmp_path / "unreadable.log"
    log_file.write_text("test content")
    log_file.chmod(0o000)  # Make file unreadable

    reader = LogReader(str(log_file))
    with pytest.raises(OSError):
        reader.find_patterns(r".*")

    log_file.chmod(0o644)  # Reset permissions for cleanup
