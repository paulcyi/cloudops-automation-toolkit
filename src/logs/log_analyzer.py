"""
Log analysis module providing log file processing and alert generation capabilities.
"""

from typing import List, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class LogAlert:
    """Data class representing a log alert with timestamp and message."""

    timestamp: datetime
    message: str
    severity: str
    pattern_matched: str


class LogAnalyzer:
    """
    A class to analyze log files and generate alerts based on pattern matching.
    """

    def __init__(self):
        """Initialize the LogAnalyzer with default patterns."""
        self.patterns: Dict[str, str] = {
            "error": r"ERROR|CRITICAL|FATAL",
            "warning": r"WARNING|WARN",
            "info": r"INFO",
        }

    def analyze_file(self, file_path: Path) -> List[LogAlert]:
        """
        Analyze a log file and return detected alerts.

        Args:
            file_path: Path to the log file to analyze

        Returns:
            List of LogAlert objects containing detected issues
        """
        alerts: List[LogAlert] = []

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    alert = self.process_line(line)
                    if alert:
                        alerts.append(alert)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Log file not found: {file_path}") from exc
        except Exception as e:
            raise RuntimeError(f"Error processing log file: {e}") from e

        return alerts

    def process_line(self, line: str) -> LogAlert | None:
        """
        Process a single log line and create an alert if patterns match.

        Args:
            line: The log line to process

        Returns:
            LogAlert if pattern matches, None otherwise
        """
        timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        timestamp_match = re.search(timestamp_pattern, line)

        if not timestamp_match:
            return None

        timestamp_str = timestamp_match.group()
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

        for severity, pattern in self.patterns.items():
            if re.search(pattern, line):
                return LogAlert(
                    timestamp=timestamp,
                    message=line.strip(),
                    severity=severity,
                    pattern_matched=pattern,
                )

        return None

    def add_pattern(self, name: str, pattern: str) -> None:
        """
        Add a new pattern for log analysis.

        Args:
            name: Name of the pattern
            pattern: Regular expression pattern to match
        """
        self.patterns[name] = pattern
