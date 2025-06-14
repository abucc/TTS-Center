import os
import boto3
from botocore.exceptions import ClientError
import logging
import io
import uuid
from typing import Optional, Tuple, Dict, Any, Union
import mimetypes

# Configure logging
logger = logging.getLogger(__name__)

class StorageManager:
    """
    Manages storage operations for TTS audio files.
    Supports both Redis caching and S3-compatible cloud storage.
    """
    def __init__(self, redis_client=None):
        # Initialize Redis client if provided
        self.redis_client = redis_client
        
        # Check if S3 storage is enabled
        self.s3_enabled = os.getenv("S3_ENABLED", "false").lower() == "true"
        self.s3_client = None
        self.s3_bucket = None
        self.s3_url = None
        
        # Base URL for publicly accessible files
        self.base_url = os.getenv("PUBLIC_URL", "").rstrip("/")
        
        if self.s3_enabled:
            try:
                # Initialize S3 client
                self.s3_bucket = os.getenv("S3_BUCKET_NAME", "")
                self.s3_endpoint_url = os.getenv("S3_ENDPOINT_URL", None)
                self.s3_region = os.getenv("S3_REGION", None)
                
                # S3 client initialization options
                s3_options = {
                    "aws_access_key_id": os.getenv("S3_ACCESS_KEY", ""),
                    "aws_secret_access_key": os.getenv("S3_SECRET_KEY", ""),
                }
                
                # Add optional parameters if they exist
                if self.s3_endpoint_url:
                    s3_options["endpoint_url"] = self.s3_endpoint_url
                if self.s3_region:
                    s3_options["region_name"] = self.s3_region
                
                # Create S3 client
                self.s3_client = boto3.client("s3", **s3_options)
                
                # Store the endpoint URL for generating file URLs
                self.s3_url = self.s3_endpoint_url
                
                logger.info(f"S3 storage initialized for bucket: {self.s3_bucket}")
                
                # Test connection by listing the bucket
                self.s3_client.list_objects_v2(Bucket=self.s3_bucket, MaxKeys=1)
                logger.info("S3 connection test successful")
                
            except Exception as e:
                logger.error(f"Failed to initialize S3 storage: {str(e)}")
                self.s3_enabled = False
    
    def store_audio(self, audio_data: bytes, cache_key: str, format: str = "wav") -> Tuple[bool, str]:
        """
        Store audio data in Redis cache and/or S3 storage.
        
        Args:
            audio_data: The raw audio data as bytes
            cache_key: The cache key for the audio
            format: Audio format (wav, mp3, etc.)
            
        Returns:
            Tuple of (success, audio_url)
        """
        # First, try to cache in Redis if available
        redis_success = False
        if self.redis_client:
            try:
                redis_success = bool(self.redis_client.set(f"audio:{cache_key}", audio_data))
                logger.debug(f"Redis cache for {cache_key}: {'Success' if redis_success else 'Failed'}")
            except Exception as e:
                logger.warning(f"Failed to cache audio in Redis: {str(e)}")
        
        # If S3 is enabled, upload to S3
        s3_success = False
        s3_url = None
        
        if self.s3_enabled and self.s3_client:
            try:
                # Generate a filename with appropriate extension
                filename = f"{cache_key}.{format}"
                
                # Determine content type based on format
                content_type = f"audio/{format}"
                
                # For Minio and other S3-compatible services, log details
                logger.info(f"Uploading audio to S3: bucket={self.s3_bucket}, filename={filename}, content_type={content_type}")
                
                # Upload to S3
                self.s3_client.upload_fileobj(
                    io.BytesIO(audio_data),
                    self.s3_bucket,
                    filename,
                    ExtraArgs={
                        'ContentType': content_type,
                        'ACL': 'public-read'  # Make the file publicly readable
                    }
                )
                
                # Generate URL following the dahopevi pattern
                s3_url = f"{self.s3_url}/{self.s3_bucket}/{filename}"
                
                s3_success = True
                logger.info(f"Uploaded audio to S3: {filename}, URL: {s3_url}")
                
            except Exception as e:
                logger.error(f"Failed to upload audio to S3: {str(e)}")
                s3_success = False
        
        # Determine the URL to return
        if s3_success and s3_url:
            # If we have a successful S3 upload with URL, return it
            return True, s3_url
        elif redis_success:
            # If Redis caching worked but S3 failed, return the API endpoint URL
            return True, f"/audio/{cache_key}"
        else:
            # Both storage methods failed
            return False, ""
    
    def get_audio(self, audio_id: str) -> Optional[bytes]:
        """
        Retrieve audio data from Redis cache.
        
        Args:
            audio_id: The audio ID to retrieve
            
        Returns:
            Audio data as bytes or None if not found
        """
        if not self.redis_client:
            return None
        
        try:
            return self.redis_client.get(f"audio:{audio_id}")
        except Exception as e:
            logger.error(f"Error retrieving audio from Redis: {str(e)}")
            return None
    
    def get_audio_url(self, cache_key: str, format: str = "wav") -> str:
        """
        Get the URL for an audio file.
        
        Args:
            cache_key: The cache key for the audio
            format: Audio format extension
            
        Returns:
            The URL for the audio file
        """
        if self.s3_enabled:
            # Construct the S3 URL - simplified to match dahopevi pattern
            filename = f"{cache_key}.{format}"
            return f"{self.s3_url}/{self.s3_bucket}/{filename}"
        else:
            # Return the API endpoint URL
            if self.base_url:
                return f"{self.base_url}/audio/{cache_key}"
            else:
                return f"/audio/{cache_key}"
