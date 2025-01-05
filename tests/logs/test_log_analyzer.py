"""Test suite for the log analyzer module."""

from datetime import datetime
from pathlib import Path

import pytest
from src.logs.log_analyzer import LogAnalyzer, LogAlert


@pytest.fixture
def test_analyzer():
    """Fixture to create a fresh LogAnalyzer instance for each test."""
    return LogAnalyzer()


def test_log_analyzer_initialization(test_analyzer):
    """Test that LogAnalyzer initializes correctly with default patterns."""
    assert test_analyzer is not None
    assert "error" in test_analyzer.patterns
    assert "warning" in test_analyzer.patterns
    assert "info" in test_analyzer.patterns


def test_process_line_with_error(test_analyzer):
    """Test processing a line containing an error."""
    test_line = "2024-01-02 10:15:30 ERROR Database connection failed"
    alert = test_analyzer.process_line(test_line)

    assert alert is not None
    assert isinstance(alert, LogAlert)
    assert alert.severity == "error"
    assert alert.timestamp == datetime(2024, 1, 2, 10, 15, 30)
    assert "Database connection failed" in alert.message


def test_process_line_no_match(test_analyzer):
    """Test processing a line with no matching patterns."""
    test_line = "2024-01-02 10:15:30 DEBUG This is a debug message"
    alert = test_analyzer.process_line(test_line)
    assert alert is None


def test_add_pattern(test_analyzer):
    """Test adding a new pattern for analysis."""
    test_analyzer.add_pattern("debug", r"DEBUG")
    assert "debug" in test_analyzer.patterns
    assert test_analyzer.patterns["debug"] == r"DEBUG"


@pytest.mark.integration
def test_analyze_file(tmp_path, test_analyzer):
    """Integration test for analyzing a log file."""
    # Create a temporary log file
    log_file = tmp_path / "test.log"
    log_content = [
        "2024-01-02 10:15:30 ERROR Database connection failed\n",
        "2024-01-02 10:15:31 INFO Server started\n",
        "2024-01-02 10:15:32 WARNING Disk usage above 80%\n",
    ]

    with open(log_file, "w", encoding="utf-8") as f:
        f.writelines(log_content)

    # Analyze the file
    alerts = test_analyzer.analyze_file(log_file)

    # Verify results
    assert len(alerts) == 3
    assert any(alert.severity == "error" for alert in alerts)
    assert any(alert.severity == "warning" for alert in alerts)
    assert any(alert.severity == "info" for alert in alerts)
