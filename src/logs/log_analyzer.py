"""
Log analysis module providing log file processing and alert generation capabilities.
Provides pattern recognition and alert generation for system and application logs.
"""

from typing import Dict, List, Optional, Pattern
import re
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass


@dataclass
class LogPattern:
    """Represents a pattern to match in logs with associated severity and description."""

    pattern: Pattern
    severity: str
    description: str


@dataclass
class LogAlert:
    """Represents an alert generated from log analysis."""

    timestamp: datetime
    severity: str
    message: str
    source: str
    pattern_matched: str


class LogAnalyzer:
    """
    A class to analyze log files and generate alerts based on pattern matching.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize the LogAnalyzer with a directory to monitor.

        Args:
            log_dir: Optional path to the directory containing log files
        """
        self.log_dir = log_dir
        self.patterns: List[LogPattern] = []
        self.alerts: List[LogAlert] = []

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # Initialize default patterns
        self._init_default_patterns()

    def _init_default_patterns(self) -> None:
        """Initialize default log patterns to match common issues."""
        default_patterns = [
            LogPattern(
                pattern=re.compile(r"error", re.IGNORECASE),
                severity="ERROR",
                description="Generic error detection",
            ),
            LogPattern(
                pattern=re.compile(r"warning", re.IGNORECASE),
                severity="WARNING",
                description="Generic warning detection",
            ),
            LogPattern(
                pattern=re.compile(r"exception|traceback", re.IGNORECASE),
                severity="ERROR",
                description="Exception stack trace detection",
            ),
            LogPattern(
                pattern=re.compile(r"failed\s+to\s+connect", re.IGNORECASE),
                severity="ERROR",
                description="Connection failure detection",
            ),
        ]
        self.patterns.extend(default_patterns)

    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """
        Extract timestamp from a log line.

        Args:
            line: The log line to process

        Returns:
            datetime object if timestamp found, None otherwise
        """
        timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        timestamp_match = re.search(timestamp_pattern, line)

        if timestamp_match:
            timestamp_str = timestamp_match.group()
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        return None

    def add_pattern(self, pattern: str, severity: str, description: str) -> None:
        """
        Add a new pattern to match in logs.

        Args:
            pattern: Regular expression pattern to match
            severity: Severity level for matching lines
            description: Description of what the pattern detects
        """
        try:
            compiled_pattern = re.compile(pattern)
            self.patterns.append(
                LogPattern(
                    pattern=compiled_pattern,
                    severity=severity.upper(),
                    description=description,
                )
            )
            self.logger.info("Added new pattern: %s", description)
        except re.error as e:
            self.logger.error("Invalid pattern '%s': %s", pattern, str(e))
            raise ValueError(f"Invalid regular expression pattern: {str(e)}") from e

    def analyze_file(self, file_path: Path) -> List[LogAlert]:
        """
        Analyze a single log file for matches against defined patterns.

        Args:
            file_path: Path to the log file to analyze

        Returns:
            List of LogAlert instances for matches found
        """
        alerts = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    timestamp = self._extract_timestamp(line) or datetime.now()
                    for pattern in self.patterns:
                        if pattern.pattern.search(line):
                            alert = LogAlert(
                                timestamp=timestamp,
                                severity=pattern.severity,
                                message=line.strip(),
                                source=f"{file_path}:{line_num}",
                                pattern_matched=pattern.description,
                            )
                            alerts.append(alert)
                            self.logger.info(
                                "Alert generated from %s: %s",
                                file_path,
                                pattern.description,
                            )
        except FileNotFoundError as exc:
            self.logger.error("Log file not found: %s", file_path)
            raise FileNotFoundError(f"Log file not found: {file_path}") from exc
        except Exception as e:
            self.logger.error("Error analyzing file %s: %s", file_path, str(e))
            raise

        return alerts

    def process_line(self, line: str) -> Optional[LogAlert]:
        """
        Process a single log line and create an alert if patterns match.

        Args:
            line: The log line to process

        Returns:
            LogAlert if pattern matches, None otherwise
        """
        timestamp = self._extract_timestamp(line)
        if not timestamp:
            return None

        for pattern in self.patterns:
            if pattern.pattern.search(line):
                return LogAlert(
                    timestamp=timestamp,
                    severity=pattern.severity,
                    message=line.strip(),
                    source="line",
                    pattern_matched=pattern.description,
                )
        return None

    def analyze_directory(self) -> List[LogAlert]:
        """
        Analyze all log files in the configured directory.

        Returns:
            List of LogAlert instances for all matches found
        """
        if not self.log_dir:
            raise ValueError("Log directory not configured")

        all_alerts = []
        try:
            for file_path in self.log_dir.glob("*.log"):
                alerts = self.analyze_file(file_path)
                all_alerts.extend(alerts)
        except Exception as e:
            self.logger.error("Error analyzing directory %s: %s", self.log_dir, str(e))
            raise

        return all_alerts
