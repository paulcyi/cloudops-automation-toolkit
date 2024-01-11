"""Test suite for the backup scheduler module."""

# Standard library imports
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# Third-party imports
import pytest

# Local imports
from src.backup.backup_scheduler import BackupScheduler
from src.backup.s3_backup import S3BackupHandler


@pytest.fixture
def mock_s3_handler():
    """Create a mock S3BackupHandler."""
    handler = Mock(spec=S3BackupHandler)
    handler.create_backup.return_value = {
        "bucket": "test-bucket",
        "key": "test-key",
        "version_id": "test-version",
    }
    return handler
