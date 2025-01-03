"""
S3 backup module for managing automated backups to AWS S3.
Provides backup creation, verification, and restoration capabilities.
"""

from typing import Optional, List, Dict
from pathlib import Path
import logging
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

class S3BackupHandler:
    """
    Handles automated backups to AWS S3 with verification and restoration capabilities.
    """
    
    def __init__(
        self,
        bucket_name: str,
        aws_region: str = "us-east-1",
        backup_prefix: str = "automated_backup"
    ):
        """
        Initialize the S3BackupHandler.
        
        Args:
            bucket_name: Name of the S3 bucket for backups
            aws_region: AWS region for the S3 bucket
            backup_prefix: Prefix for backup objects in S3
        """
        self.bucket_name = bucket_name
        self.backup_prefix = backup_prefix
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3', region_name=aws_region)
            self._verify_bucket_access()
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise
            
    def _verify_bucket_access(self) -> None:
        """Verify access to the S3 bucket."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                self.logger.error(f"Bucket {self.bucket_name} does not exist")
            elif error_code == '403':
                self.logger.error(f"Access denied to bucket {self.bucket_name}")
            raise
            
    def create_backup(self, file_path: Path, retention_days: Optional[int] = 30) -> Dict[str, str]:
        """
        Create a backup of the specified file in S3.
        
        Args:
            file_path: Path to the file to backup
            retention_days: Number of days to retain the backup
            
        Returns:
            Dict containing backup details (bucket, key, version)
        """
        try:
            # Generate S3 key with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"{self.backup_prefix}/{file_path.name}_{timestamp}"
            
            # Upload file to S3
            with open(file_path, 'rb') as file:
                response = self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=file,
                    Metadata={
                        'retention_days': str(retention_days),
                        'original_path': str(file_path),
                        'backup_date': timestamp
                    }
                )
            
            self.logger.info(f"Successfully created backup: {s3_key}")
            
            return {
                'bucket': self.bucket_name,
                'key': s3_key,
                'version_id': response.get('VersionId', 'None')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create backup for {file_path}: {str(e)}")
            raise
            
    def verify_backup(self, backup_info: Dict[str, str]) -> bool:
        """
        Verify the integrity of a backup in S3.
        
        Args:
            backup_info: Dict containing backup details
            
        Returns:
            bool indicating if backup is valid
        """
        try:
            response = self.s3_client.head_object(
                Bucket=backup_info['bucket'],
                Key=backup_info['key']
            )
            return True
        except ClientError as e:
            self.logger.error(f"Failed to verify backup: {str(e)}")
            return False
            
    def list_backups(self, max_items: int = 100) -> List[Dict[str, str]]:
        """
        List available backups in S3.
        
        Args:
            max_items: Maximum number of backups to list
            
        Returns:
            List of backup details
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.backup_prefix,
                MaxKeys=max_items
            )
            
            backups = []
            for obj in response.get('Contents', []):
                backup_info = {
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                }
                
                # Get additional metadata
                try:
                    metadata = self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    backup_info['metadata'] = metadata.get('Metadata', {})
                except ClientError:
                    backup_info['metadata'] = {}
                    
                backups.append(backup_info)
                
            return backups
            
        except ClientError as e:
            self.logger.error(f"Failed to list backups: {str(e)}")
            raise
            
    def restore_backup(
        self,
        backup_key: str,
        destination_path: Path,
        overwrite: bool = False
    ) -> bool:
        """
        Restore a backup from S3.
        
        Args:
            backup_key: S3 key of the backup to restore
            destination_path: Path where to restore the backup
            overwrite: Whether to overwrite existing files
            
        Returns:
            bool indicating if restoration was successful
        """
        try:
            if destination_path.exists() and not overwrite:
                raise FileExistsError(
                    f"Destination path {destination_path} exists and overwrite is False"
                )
                
            # Download backup from S3
            with open(destination_path, 'wb') as file:
                self.s3_client.download_fileobj(
                    self.bucket_name,
                    backup_key,
                    file
                )
                
            self.logger.info(
                f"Successfully restored backup {backup_key} to {destination_path}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup {backup_key}: {str(e)}")
            return False