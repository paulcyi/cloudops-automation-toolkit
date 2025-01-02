"""Test suite for the log analyzer module."""

import pytest
from pathlib import Path
from datetime import datetime
from src.logs.log_analyzer import LogAnalyzer, LogAlert


@pytest.fixture
def log_analyzer():
    """Fixture to create a fresh LogAnalyzer instance for each test."""
    return LogAnalyzer()


def test_log_analyzer_initialization(log_analyzer):
    """Test that LogAnalyzer initializes correctly with default patterns."""
    assert log_analyzer is not None
    assert 'error' in log_analyzer.patterns
    assert 'warning' in log_analyzer.patterns
    assert 'info' in log_analyzer.patterns


def test_process_line_with_error(log_analyzer):
    """Test processing a line containing an error."""
    test_line = "2024-01-02 10:15:30 ERROR Database connection failed"
    alert = log_analyzer._process_line(test_line)
    
    assert alert is not None
    assert isinstance(alert, LogAlert)
    assert alert.severity == 'error'
    assert alert.timestamp == datetime(2024, 1, 2, 10, 15, 30)
    assert "Database connection failed" in alert.message


def test_process_line_no_match(log_analyzer):
    """Test processing a line with no matching patterns."""
    test_line = "2024-01-02 10:15:30 DEBUG This is a debug message"
    alert = log_analyzer._process_line(test_line)
    assert alert is None


def test_add_pattern(log_analyzer):
    """Test adding a new pattern for analysis."""
    log_analyzer.add_pattern('debug', r'DEBUG')
    assert 'debug' in log_analyzer.patterns
    assert log_analyzer.patterns['debug'] == r'DEBUG'


@pytest.mark.integration
def test_analyze_file(tmp_path, log_analyzer):
    """Integration test for analyzing a log file."""
    # Create a temporary log file
    log_file = tmp_path / "test.log"
    log_content = [
        "2024-01-02 10:15:30 ERROR Database connection failed\n",
        "2024-01-02 10:15:31 INFO Server started\n",
        "2024-01-02 10:15:32 WARNING Disk usage above 80%\n"
    ]
    
    with open(log_file, 'w') as f:
        f.writelines(log_content)
    
    # Analyze the file
    alerts = log_analyzer.analyze_file(log_file)
    
    # Verify results
    assert len(alerts) == 3
    assert any(alert.severity == 'error' for alert in alerts)
    assert any(alert.severity == 'warning' for alert in alerts)
    assert any(alert.severity == 'info' for alert in alerts)