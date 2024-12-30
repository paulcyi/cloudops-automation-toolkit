from typing import List, Dict
import re
from datetime import datetime

class LogReader:
    """A class to read and analyze log files with pattern recognition capabilities."""
    
    def __init__(self, log_path: str):
        """Initialize the LogReader with a path to the log file.
        
        Args:
            log_path (str): Path to the log file to analyze
        """
        self.log_path = log_path
        
    def read_log(self) -> List[str]:
        """Read all lines from the log file.
        
        Returns:
            List[str]: List of lines from the log file
        """
        try:
            with open(self.log_path, 'r', encoding='utf-8') as file:
                return file.readlines()
        except FileNotFoundError:
            return []
            
    def find_patterns(self, pattern: str) -> List[Dict[str, str]]:
        """Search for specific patterns in log entries.
        
        Args:
            pattern (str): Regular expression pattern to search for
            
        Returns:
            List[Dict[str, str]]: List of matches with timestamp and content
        """
        matches = []
        try:
            timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'  # yyyy-mm-dd HH:MM:SS
            
            for line in self.read_log():
                if re.search(pattern, line):
                    timestamp_match = re.search(timestamp_pattern, line)
                    timestamp = timestamp_match.group() if timestamp_match else "Unknown"
                    
                    matches.append({
                        "timestamp": timestamp,
                        "content": line.strip(),
                        "pattern_match": re.search(pattern, line).group()
                    })
                    
            return matches
        except Exception as e:
            print(f"Error searching patterns: {e}")
            return []