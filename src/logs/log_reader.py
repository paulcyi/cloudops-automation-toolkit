"""
Log reading module providing file parsing and pattern matching capabilities.
"""

from typing import List, Dict, Optional
import re
import logging
from datetime import datetime
from pathlib import Path


class LogReader:
    """A class to read and analyze log files with pattern recognition capabilities."""

    def __init__(self, log_path: str):
        """Initialize the LogReader with a path to the log file.

        Args:
            log_path: Path to the log file to analyze
        """
        self.log_path = log_path
        self.logger = logging.getLogger(__name__)

    def read_log(self) -> List[str]:
        """Read all lines from the log file.

        Returns:
            List of lines from the log file

        Raises:
            FileNotFoundError: If the log file doesn't exist
            OSError: If there are issues reading the file
        """
        try:
            with open(self.log_path, "r", encoding="utf-8") as file:
                return file.readlines()
        except FileNotFoundError:
            self.logger.warning("Log file not found: %s", self.log_path)
            return []
        except OSError as e:
            self.logger.error("Error reading log file %s: %s", self.log_path, e)
            raise

    def _extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from a log line.

        Args:
            line: The log line to process

        Returns:
            Timestamp string if found, None otherwise
        """
        timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        timestamp_match = re.search(timestamp_pattern, line)
        return timestamp_match.group() if timestamp_match else None

    def find_patterns(self, pattern: str) -> List[Dict[str, str]]:
        """Search for specific patterns in log entries.

        Args:
            pattern: Regular expression pattern to search for

        Returns:
            List of matches with timestamp and content

        Raises:
            ValueError: If the pattern is invalid
            OSError: If there are issues reading the file
        """
        matches = []
        try:
            compiled_pattern = re.compile(pattern)
        except re.error as e:
            self.logger.error("Invalid regex pattern '%s': %s", pattern, e)
            raise ValueError(f"Invalid regular expression pattern: {e}") from e

        try:
            for line in self.read_log():
                if compiled_pattern.search(line):
                    timestamp = self._extract_timestamp(line) or "Unknown"
                    pattern_match = compiled_pattern.search(line)

                    if pattern_match:  # Extra safety check
                        matches.append(
                            {
                                "timestamp": timestamp,
                                "content": line.strip(),
                                "pattern_match": pattern_match.group(),
                            }
                        )

            self.logger.info(
                "Found %d matches for pattern '%s' in %s",
                len(matches),
                pattern,
                self.log_path,
            )
            return matches

        except OSError as e:
            self.logger.error("Error processing log file %s: %s", self.log_path, e)
            raise

    def find_patterns_in_timerange(
        self, pattern: str, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, str]]:
        """Search for patterns within a specific time range.

        Args:
            pattern: Regular expression pattern to search for
            start_time: Start of the time range
            end_time: End of the time range

        Returns:
            List of matches within the specified time range

        Raises:
            ValueError: If the pattern is invalid or time range is incorrect
            OSError: If there are issues reading the file
        """
        if start_time > end_time:
            raise ValueError("Start time must be before end time")

        matches = []
        all_matches = self.find_patterns(pattern)

        for match in all_matches:
            try:
                timestamp = datetime.strptime(match["timestamp"], "%Y-%m-%d %H:%M:%S")
                if start_time <= timestamp <= end_time:
                    matches.append(match)
            except ValueError:
                # Skip entries with invalid timestamps
                continue

        self.logger.info(
            "Found %d matches in timerange for pattern '%s'", len(matches), pattern
        )
        return matches
