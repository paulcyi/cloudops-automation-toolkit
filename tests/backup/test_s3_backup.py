"""Tests for the S3 backup handler."""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from src.backup.s3_backup import S3BackupHandler

@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    with patch('boto3.client') as mock_client:
        s3_client = Mock()
        mock_client.return_value = s3_client
        yield s3_client

@pytest.fixture
def backup_handler(mock_s3_client):
    """Create a backup handler with mocked S3 client."""
    handler = S3BackupHandler('test-bucket')
    return handler

@pytest.fixture
def sample_file(tmp_path):
    """Create a sample file for testing."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Test content")
    return file_path

def test_initialization(mock_s3_client):
    """Test successful initialization of backup handler."""
    handler = S3BackupHandler('test-bucket')
    assert handler.bucket_name == 'test-bucket'
    mock_s3_client.head_bucket.assert_called_once_with(Bucket='test-bucket')

def test_initialization_bucket_not_found(mock_s3_client):
    """Test initialization with non-existent bucket."""
    error_response = {
        'Error': {
            'Code': '404',
            'Message': 'Not Found'
        }
    }
    mock_s3_client.head_bucket.side_effect = ClientError(error_response, 'HeadBucket')
    
    with pytest.raises(ClientError):
        S3BackupHandler('non-existent-bucket')

def test_create_backup(backup_handler, sample_file):
    """Test creating a backup."""
    # Mock successful upload
    backup_handler.s3_client.put_object.return_value = {'VersionId': 'test-version'}
    
    # Create backup
    result = backup_handler.create_backup(sample_file)
    
    # Verify result
    assert result['bucket'] == 'test-bucket'
    assert result['version_id'] == 'test-version'
    assert sample_file.name in result['key']
    
    # Verify S3 client called correctly
    backup_handler.s3_client.put_object.assert_called_once()

def test_verify_backup(backup_handler):
    """Test backup verification."""
    backup_info = {
        'bucket': 'test-bucket',
        'key': 'test-key',
        'version_id': 'test-version'
    }
    
    # Test successful verification
    assert backup_handler.verify_backup(backup_info) is True
    
    # Test failed verification
    error_response = {
        'Error': {
            'Code': '404',
            'Message': 'Not Found'
        }
    }
    backup_handler.s3_client.head_object.side_effect = ClientError(
        error_response, 'HeadObject'
    )
    assert backup_handler.verify_backup(backup_info) is False

def test_list_backups(backup_handler):
    """Test listing backups."""
    # Mock S3 response
    mock_date = datetime.now()
    backup_handler.s3_client.list_objects_v2.return_value = {
        'Contents': [
            {
                'Key': 'backup1',
                'Size': 100,
                'LastModified': mock_date
            }
        ]
    }
    
    # Get backup list
    backups = backup_handler.list_backups()
    
    # Verify response
    assert len(backups) == 1
    assert backups[0]['key'] == 'backup1'
    assert backups[0]['size'] == 100
    assert backups[0]['last_modified'] == mock_date.isoformat()

def test_restore_backup(backup_handler, tmp_path):
    """Test backup restoration."""
    destination = tmp_path / "restored_file.txt"
    
    # Test successful restoration
    assert backup_handler.restore_backup('test-key', destination) is True
    
    # Test restoration with existing file
    with pytest.raises(FileExistsError):
        backup_handler.restore_backup('test-key', destination, overwrite=False)
    
    # Test successful overwrite
    assert backup_handler.restore_backup('test-key', destination, overwrite=True) is True

@pytest.mark.integration
def test_full_backup_cycle(backup_handler, sample_file, tmp_path):
    """Integration test for full backup cycle."""
    # Create backup
    backup_info = backup_handler.create_backup(sample_file)
    
    # Verify backup exists
    assert backup_handler.verify_backup(backup_info) is True
    
    # List backups
    backups = backup_handler.list_backups()
    assert len(backups) > 0
    
    # Restore backup
    restore_path = tmp_path / "restored_file.txt"
    assert backup_handler.restore_backup(backup_info['key'], restore_path) is True