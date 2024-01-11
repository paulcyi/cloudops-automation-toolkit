"""Base module for S3 operations."""

import logging
from typing import Dict, List, Optional
import boto3
from botocore.exceptions import ClientError


class S3BaseError(Exception):
    """Base exception for S3 operations."""


class S3BaseHandler:
    """Base class for S3 operations with common functionality."""

    def __init__(
        self,
        bucket_name: str,
        aws_region: str = "us-east-1",
        backup_prefix: str = "automated_backup",
    ) -> None:
        """Initialize the base S3 handler."""
        self.bucket_name = bucket_name
        self.backup_prefix = backup_prefix
        self.logger = logging.getLogger(__name__)

        try:
            self.s3_client = boto3.client("s3", region_name=aws_region)
            self._verify_bucket_access()
        except Exception as error:
            self.logger.error("Failed to initialize S3 client: %s", str(error))
            raise S3BaseError(f"S3 client initialization failed: {str(error)}") from error

    def _verify_bucket_access(self) -> None:
        """Verify access to the S3 bucket."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as error:
            error_code = error.response.get("Error", {}).get("Code", "Unknown")
            error_mapping = {
                "404": f"Bucket {self.bucket_name} does not exist",
                "403": f"Access denied to bucket {self.bucket_name}",
            }
            msg = error_mapping.get(
                error_code, f"Error accessing bucket {self.bucket_name}: {error_code}"
            )
            self.logger.error(msg)
            raise S3BaseError(msg) from error

    def _get_object_metadata(self, key: str) -> Dict[str, str]:
        """Get metadata for an S3 object."""
        try:
            metadata = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return metadata.get("Metadata", {})
        except ClientError as error:
            self.logger.warning(
                "Failed to fetch metadata for %s: %s", key, str(error)
            )
            return {}