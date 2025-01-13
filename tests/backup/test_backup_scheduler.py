"""Test suite for the backup scheduler module."""

# pylint: disable=protected-access
# pylint: disable=unused-argument

# Standard library imports
import hashlib
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# Third-party imports
import pytest
import schedule
from botocore.exceptions import ClientError

# Local imports
from src.backup.backup_scheduler import (
    BackupScheduler,
    BackupSchedulerError,
    BackupVerificationError,
    BackupMetadataError,
    BackupMetadata,
    BackupConfig,
)


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    with patch("boto3.client") as mock_client:
        s3_client = Mock()
        # Configure head_bucket to succeed
        s3_client.head_bucket.return_value = {}
        mock_client.return_value = s3_client
        yield s3_client


@pytest.fixture
def backup_scheduler(mock_s3_client):
    """Create a BackupScheduler instance with mocked S3 client."""
    config = BackupConfig()
    scheduler = BackupScheduler("test-bucket", config=config)
    return scheduler


@pytest.fixture
def sample_file(tmp_path):
    """Create a sample file for testing."""
    file_path = tmp_path / "test_file.txt"
    content = "Test content for backup verification"
    file_path.write_text(content)
    return file_path


def test_initialization(backup_scheduler):
    """Test BackupScheduler initialization."""
    assert backup_scheduler.bucket_name == "test-bucket"
    assert backup_scheduler.max_retries == 3
    assert isinstance(backup_scheduler.scheduler, schedule.Scheduler)
    assert backup_scheduler.jobs == {}


def test_calculate_file_hash(backup_scheduler, sample_file):
    """Test file hash calculation."""
    calculated_hash = backup_scheduler._calculate_file_hash(sample_file)

    # Calculate expected hash
    sha256_hash = hashlib.sha256()
    with open(sample_file, "rb") as f:
        sha256_hash.update(f.read())
    expected_hash = sha256_hash.hexdigest()

    assert calculated_hash == expected_hash


def test_verify_backup_success(backup_scheduler, sample_file, mock_s3_client):
    """Test successful backup verification."""
    # Calculate file hash
    file_hash = backup_scheduler._calculate_file_hash(sample_file)

    # Mock S3 head_object response
    mock_s3_client.head_object.return_value = {"Metadata": {"sha256_hash": file_hash}}

    assert backup_scheduler._verify_backup(sample_file, "test-key")
    mock_s3_client.head_object.assert_called_once_with(
        Bucket="test-bucket", Key="test-key"
    )


def test_verify_backup_failure(backup_scheduler, sample_file, mock_s3_client):
    """Test backup verification failure."""
    # Mock S3 head_object response with different hash
    mock_s3_client.head_object.return_value = {
        "Metadata": {"sha256_hash": "different_hash"}
    }

    assert not backup_scheduler._verify_backup(sample_file, "test-key")


def test_verify_backup_missing_hash(backup_scheduler, sample_file, mock_s3_client):
    """Test backup verification with missing hash metadata."""
    mock_s3_client.head_object.return_value = {"Metadata": {}}

    with pytest.raises(BackupVerificationError, match="No hash found in metadata"):
        backup_scheduler._verify_backup(sample_file, "test-key")


def test_perform_backup_success(backup_scheduler, sample_file, mock_s3_client):
    """Test successful backup operation."""
    # Calculate file hash
    file_hash = backup_scheduler._calculate_file_hash(sample_file)

    # Mock successful upload
    mock_s3_client.put_object.return_value = {"VersionId": "test-version"}

    # Mock successful verification
    mock_s3_client.head_object.return_value = {"Metadata": {"sha256_hash": file_hash}}

    result = backup_scheduler._perform_backup(sample_file, 30)

    assert result["bucket"] == "test-bucket"
    assert "key" in result
    assert result["version_id"] == "test-version"
    assert result["hash"] == file_hash


def test_perform_backup_retry_success(backup_scheduler, sample_file, mock_s3_client):
    """Test backup operation succeeding after retry."""
    file_hash = backup_scheduler._calculate_file_hash(sample_file)

    # Mock upload failing once then succeeding
    mock_s3_client.put_object.side_effect = [
        ClientError({"Error": {"Code": "500", "Message": "Test error"}}, "put_object"),
        {"VersionId": "test-version"},
    ]

    # Mock successful verification
    mock_s3_client.head_object.return_value = {"Metadata": {"sha256_hash": file_hash}}

    result = backup_scheduler._perform_backup(sample_file, 30)

    assert result["version_id"] == "test-version"
    assert mock_s3_client.put_object.call_count == 2


def test_perform_backup_all_retries_failed(
    backup_scheduler, sample_file, mock_s3_client
):
    """Test backup operation failing all retry attempts."""
    # Mock upload always failing
    error = ClientError(
        {"Error": {"Code": "500", "Message": "Test error"}}, "put_object"
    )
    mock_s3_client.put_object.side_effect = error

    with pytest.raises(BackupSchedulerError, match="Backup failed after 3 attempts"):
        backup_scheduler._perform_backup(sample_file, 30)

    assert mock_s3_client.put_object.call_count == 3  # Verify max retries


def test_schedule_backup(backup_scheduler, sample_file):
    """Test scheduling a backup job."""
    job_id = backup_scheduler.schedule_backup(sample_file, "minutes", 5)

    assert job_id in backup_scheduler.jobs
    assert backup_scheduler.jobs[job_id] is not None


def test_schedule_backup_invalid_file(backup_scheduler):
    """Test scheduling backup with non-existent file."""
    with pytest.raises(FileNotFoundError):
        backup_scheduler.schedule_backup(Path("nonexistent.txt"), "minutes", 5)


def test_schedule_backup_invalid_schedule(backup_scheduler, sample_file):
    """Test scheduling backup with invalid schedule type."""
    with pytest.raises(ValueError, match="Invalid schedule type"):
        backup_scheduler.schedule_backup(sample_file, "invalid", 5)


def test_metadata_validation_success(backup_scheduler):
    """Test successful metadata validation."""
    valid_metadata = {
        "original_path": "/path/to/file.txt",
        "backup_date": "2024-01-15T10:30:00",
        "retention_days": "30",
        "sha256_hash": "a" * 64,
        "size_bytes": "1024",
    }

    metadata = backup_scheduler._validate_metadata(valid_metadata)
    assert isinstance(metadata, BackupMetadata)
    assert metadata.retention_days == 30
    assert metadata.size_bytes == 1024


def test_metadata_validation_missing_fields(backup_scheduler):
    """Test metadata validation with missing fields."""
    invalid_metadata = {
        "original_path": "/path/to/file.txt",
        "backup_date": "2024-01-15T10:30:00",
    }

    with pytest.raises(BackupMetadataError, match="Missing required metadata fields"):
        backup_scheduler._validate_metadata(invalid_metadata)


def test_metadata_validation_invalid_retention(backup_scheduler):
    """Test metadata validation with invalid retention days."""
    invalid_metadata = {
        "original_path": "/path/to/file.txt",
        "backup_date": "2024-01-15T10:30:00",
        "retention_days": "999999",
        "sha256_hash": "a" * 64,
    }

    with pytest.raises(BackupMetadataError, match="Retention days must be between"):
        backup_scheduler._validate_metadata(invalid_metadata)


def test_backup_statistics(backup_scheduler):
    """Test backup statistics calculation."""
    # Add some test metadata
    test_metadata = BackupMetadata(
        file_path="/test/path.txt",
        backup_date="2024-01-15T10:30:00",
        retention_days=30,
        sha256_hash="a" * 64,
        size_bytes=1024,
        status="success",
    )

    backup_scheduler._update_metadata_history(test_metadata)

    stats = backup_scheduler.get_backup_statistics()
    assert stats["success_rate"] == 100.0
    assert stats["total_backups"] == 1
    assert stats["average_size_mb"] == 1024 / 1024 / 1024  # Convert bytes to MB
