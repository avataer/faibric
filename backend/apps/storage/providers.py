"""
Storage providers for local and cloud storage.
"""
import os
import logging
import hashlib
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional, Dict
from dataclasses import dataclass
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Result of a file upload."""
    success: bool
    file_path: str = ''
    file_url: str = ''
    error: str = ''


@dataclass
class FileInfo:
    """File information."""
    exists: bool
    size: int = 0
    content_type: str = ''
    last_modified: str = ''


class BaseStorageProvider(ABC):
    """Base class for storage providers."""
    
    @abstractmethod
    def upload(
        self,
        file: BinaryIO,
        path: str,
        content_type: str = 'application/octet-stream'
    ) -> UploadResult:
        """Upload a file."""
        pass
    
    @abstractmethod
    def download(self, path: str) -> Optional[bytes]:
        """Download a file."""
        pass
    
    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete a file."""
        pass
    
    @abstractmethod
    def get_url(self, path: str, expires_in: int = 3600) -> str:
        """Get a URL for the file."""
        pass
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    def get_info(self, path: str) -> FileInfo:
        """Get file info."""
        pass


class LocalStorageProvider(BaseStorageProvider):
    """Local filesystem storage."""
    
    def __init__(self, base_path: str = None, base_url: str = None):
        self.base_path = base_path or os.path.join(settings.MEDIA_ROOT, 'storage')
        self.base_url = base_url or '/media/storage/'
        os.makedirs(self.base_path, exist_ok=True)
    
    def _get_full_path(self, path: str) -> str:
        return os.path.join(self.base_path, path)
    
    def upload(
        self,
        file: BinaryIO,
        path: str,
        content_type: str = 'application/octet-stream'
    ) -> UploadResult:
        try:
            full_path = self._get_full_path(path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'wb') as f:
                for chunk in iter(lambda: file.read(8192), b''):
                    f.write(chunk)
            
            return UploadResult(
                success=True,
                file_path=path,
                file_url=self.base_url + path
            )
        except Exception as e:
            logger.error(f"Local upload error: {e}")
            return UploadResult(success=False, error=str(e))
    
    def download(self, path: str) -> Optional[bytes]:
        try:
            full_path = self._get_full_path(path)
            with open(full_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Local download error: {e}")
            return None
    
    def delete(self, path: str) -> bool:
        try:
            full_path = self._get_full_path(path)
            if os.path.exists(full_path):
                os.remove(full_path)
            return True
        except Exception as e:
            logger.error(f"Local delete error: {e}")
            return False
    
    def get_url(self, path: str, expires_in: int = 3600) -> str:
        return self.base_url + path
    
    def exists(self, path: str) -> bool:
        return os.path.exists(self._get_full_path(path))
    
    def get_info(self, path: str) -> FileInfo:
        full_path = self._get_full_path(path)
        if not os.path.exists(full_path):
            return FileInfo(exists=False)
        
        stat = os.stat(full_path)
        return FileInfo(
            exists=True,
            size=stat.st_size,
            last_modified=str(stat.st_mtime)
        )


class S3StorageProvider(BaseStorageProvider):
    """Amazon S3 / Cloudflare R2 / compatible storage."""
    
    def __init__(
        self,
        bucket_name: str,
        access_key: str,
        secret_key: str,
        region: str = 'us-east-1',
        endpoint_url: str = None,
        cdn_url: str = None
    ):
        self.bucket_name = bucket_name
        self.region = region
        self.endpoint_url = endpoint_url
        self.cdn_url = cdn_url
        
        import boto3
        
        self.client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            endpoint_url=endpoint_url
        )
    
    def upload(
        self,
        file: BinaryIO,
        path: str,
        content_type: str = 'application/octet-stream'
    ) -> UploadResult:
        try:
            self.client.upload_fileobj(
                file,
                self.bucket_name,
                path,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'private'
                }
            )
            
            url = self.get_url(path)
            
            return UploadResult(
                success=True,
                file_path=path,
                file_url=url
            )
        except Exception as e:
            logger.error(f"S3 upload error: {e}")
            return UploadResult(success=False, error=str(e))
    
    def download(self, path: str) -> Optional[bytes]:
        try:
            import io
            buffer = io.BytesIO()
            self.client.download_fileobj(self.bucket_name, path, buffer)
            buffer.seek(0)
            return buffer.read()
        except Exception as e:
            logger.error(f"S3 download error: {e}")
            return None
    
    def delete(self, path: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=path)
            return True
        except Exception as e:
            logger.error(f"S3 delete error: {e}")
            return False
    
    def get_url(self, path: str, expires_in: int = 3600) -> str:
        if self.cdn_url:
            return f"{self.cdn_url.rstrip('/')}/{path}"
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': path},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"S3 URL generation error: {e}")
            return ''
    
    def exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=path)
            return True
        except:
            return False
    
    def get_info(self, path: str) -> FileInfo:
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=path)
            return FileInfo(
                exists=True,
                size=response['ContentLength'],
                content_type=response.get('ContentType', ''),
                last_modified=str(response.get('LastModified', ''))
            )
        except:
            return FileInfo(exists=False)


def get_storage_provider(config: 'StorageConfig') -> BaseStorageProvider:
    """Get storage provider based on config."""
    if config.provider == 's3' or config.provider == 'r2':
        return S3StorageProvider(
            bucket_name=config.bucket_name,
            access_key=config.access_key,
            secret_key=config.secret_key,
            region=config.region,
            endpoint_url=config.endpoint_url or None,
            cdn_url=config.cdn_url or None
        )
    
    # Default to local storage
    return LocalStorageProvider()


def calculate_file_hash(file: BinaryIO) -> Dict[str, str]:
    """Calculate MD5 and SHA256 hashes for a file."""
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    
    file.seek(0)
    for chunk in iter(lambda: file.read(8192), b''):
        md5.update(chunk)
        sha256.update(chunk)
    
    file.seek(0)
    
    return {
        'md5': md5.hexdigest(),
        'sha256': sha256.hexdigest()
    }









