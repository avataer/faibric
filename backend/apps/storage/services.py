"""
Storage service for file management.
"""
import os
import logging
import mimetypes
from typing import BinaryIO, List, Dict, Optional, Tuple
from io import BytesIO
from django.utils import timezone
from django.db import transaction
from PIL import Image

from .models import StorageConfig, Folder, File, StorageUsage
from .providers import get_storage_provider, calculate_file_hash

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Process and optimize images."""
    
    @staticmethod
    def get_image_dimensions(file: BinaryIO) -> Tuple[int, int]:
        """Get image width and height."""
        file.seek(0)
        try:
            with Image.open(file) as img:
                return img.size
        except Exception:
            return (0, 0)
        finally:
            file.seek(0)
    
    @staticmethod
    def optimize_image(
        file: BinaryIO,
        max_dimension: int = 2048,
        quality: int = 85,
        output_format: str = None
    ) -> Tuple[BytesIO, str]:
        """Optimize an image and return the result."""
        file.seek(0)
        
        with Image.open(file) as img:
            # Convert RGBA to RGB for JPEG
            if img.mode == 'RGBA' and output_format in ['JPEG', 'JPG']:
                img = img.convert('RGB')
            
            # Resize if needed
            width, height = img.size
            if max(width, height) > max_dimension:
                ratio = max_dimension / max(width, height)
                new_size = (int(width * ratio), int(height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
            
            # Determine output format
            if not output_format:
                output_format = img.format or 'JPEG'
            
            # Save to buffer
            buffer = BytesIO()
            save_kwargs = {}
            
            if output_format.upper() in ['JPEG', 'JPG']:
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
            elif output_format.upper() == 'PNG':
                save_kwargs['optimize'] = True
            elif output_format.upper() == 'WEBP':
                save_kwargs['quality'] = quality
            
            img.save(buffer, format=output_format, **save_kwargs)
            buffer.seek(0)
            
            content_type = f"image/{output_format.lower()}"
            if output_format.upper() == 'JPG':
                content_type = 'image/jpeg'
            
            return buffer, content_type
    
    @staticmethod
    def create_thumbnail(
        file: BinaryIO,
        size: int,
        output_format: str = 'JPEG'
    ) -> BytesIO:
        """Create a square thumbnail."""
        file.seek(0)
        
        with Image.open(file) as img:
            # Convert to RGB if needed
            if img.mode == 'RGBA' and output_format in ['JPEG', 'JPG']:
                img = img.convert('RGB')
            
            # Create square thumbnail (center crop)
            width, height = img.size
            min_dim = min(width, height)
            
            left = (width - min_dim) // 2
            top = (height - min_dim) // 2
            right = left + min_dim
            bottom = top + min_dim
            
            img = img.crop((left, top, right, bottom))
            img = img.resize((size, size), Image.LANCZOS)
            
            buffer = BytesIO()
            img.save(buffer, format=output_format, quality=80)
            buffer.seek(0)
            
            return buffer


class StorageService:
    """
    Service for file storage operations.
    """
    
    def __init__(self, tenant: 'Tenant'):
        self.tenant = tenant
        self._config = None
        self._provider = None
    
    @property
    def config(self) -> StorageConfig:
        if self._config is None:
            self._config, _ = StorageConfig.objects.get_or_create(
                tenant=self.tenant
            )
        return self._config
    
    @property
    def provider(self):
        if self._provider is None:
            self._provider = get_storage_provider(self.config)
        return self._provider
    
    def _get_storage_path(self, filename: str) -> str:
        """Generate storage path for a file."""
        ext = os.path.splitext(filename)[1].lower()
        import uuid
        unique_name = f"{uuid.uuid4().hex}{ext}"
        now = timezone.now()
        return f"{self.tenant.id}/{now.year}/{now.month:02d}/{unique_name}"
    
    def _is_image(self, content_type: str) -> bool:
        """Check if content type is an image."""
        return content_type.startswith('image/')
    
    def _validate_file(self, file: BinaryIO, filename: str, content_type: str) -> None:
        """Validate file against config rules."""
        # Check file size
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)
        
        max_size = self.config.max_file_size_mb * 1024 * 1024
        if size > max_size:
            raise ValueError(f"File too large. Max size: {self.config.max_file_size_mb}MB")
        
        # Check file extension
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        
        if self._is_image(content_type):
            if ext not in self.config.allowed_image_types:
                raise ValueError(f"Image type not allowed: {ext}")
        else:
            if ext not in self.config.allowed_file_types:
                raise ValueError(f"File type not allowed: {ext}")
        
        # Check storage quota
        usage, _ = StorageUsage.objects.get_or_create(tenant=self.tenant)
        max_storage = self.config.max_storage_gb * 1024 * 1024 * 1024
        if usage.total_size_bytes + size > max_storage:
            raise ValueError("Storage quota exceeded")
    
    @transaction.atomic
    def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str = None,
        folder: Folder = None,
        owner_id: str = '',
        owner_type: str = 'user',
        is_public: bool = False
    ) -> File:
        """Upload a file."""
        # Detect content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or 'application/octet-stream'
        
        # Validate
        self._validate_file(file, filename, content_type)
        
        # Calculate hashes
        hashes = calculate_file_hash(file)
        
        # Get file size
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        # Process image if applicable
        is_image = self._is_image(content_type)
        image_width = None
        image_height = None
        thumbnails = {}
        
        if is_image and self.config.auto_optimize_images:
            # Get original dimensions
            image_width, image_height = ImageProcessor.get_image_dimensions(file)
            
            # Optimize image
            optimized, content_type = ImageProcessor.optimize_image(
                file,
                max_dimension=self.config.max_image_dimension,
                quality=self.config.jpeg_quality
            )
            file = optimized
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
        
        # Generate storage path
        ext = os.path.splitext(filename)[1].lower()
        storage_path = self._get_storage_path(filename)
        
        # Upload to storage
        result = self.provider.upload(file, storage_path, content_type)
        
        if not result.success:
            raise ValueError(f"Upload failed: {result.error}")
        
        # Generate thumbnails for images
        if is_image and self.config.generate_thumbnails:
            file.seek(0)
            for size in self.config.thumbnail_sizes:
                try:
                    thumb = ImageProcessor.create_thumbnail(file, size)
                    thumb_path = storage_path.replace(ext, f'_thumb_{size}{ext}')
                    thumb_result = self.provider.upload(
                        thumb,
                        thumb_path,
                        content_type
                    )
                    if thumb_result.success:
                        thumbnails[str(size)] = thumb_result.file_url
                except Exception as e:
                    logger.warning(f"Thumbnail generation failed for size {size}: {e}")
        
        # Create file record
        file_record = File.objects.create(
            tenant=self.tenant,
            folder=folder,
            original_name=filename,
            stored_name=os.path.basename(storage_path),
            file_path=storage_path,
            file_url=result.file_url,
            content_type=content_type,
            file_size=file_size,
            file_extension=ext.lstrip('.'),
            md5_hash=hashes['md5'],
            sha256_hash=hashes['sha256'],
            is_image=is_image,
            image_width=image_width,
            image_height=image_height,
            thumbnails=thumbnails,
            owner_id=owner_id,
            owner_type=owner_type,
            is_public=is_public
        )
        
        # Update usage
        self._update_usage(file_size, is_image)
        
        return file_record
    
    def _update_usage(self, size_change: int, is_image: bool):
        """Update storage usage stats."""
        usage, _ = StorageUsage.objects.get_or_create(tenant=self.tenant)
        usage.total_files += 1
        usage.total_size_bytes += size_change
        
        if is_image:
            usage.image_count += 1
            usage.image_size_bytes += size_change
        else:
            usage.other_count += 1
            usage.other_size_bytes += size_change
        
        usage.save()
    
    def get_file(self, file_id: str) -> Optional[File]:
        """Get a file by ID."""
        try:
            return File.objects.get(
                id=file_id,
                tenant=self.tenant,
                is_deleted=False
            )
        except File.DoesNotExist:
            return None
    
    def download_file(self, file: File) -> Optional[bytes]:
        """Download file content."""
        file.increment_download()
        return self.provider.download(file.file_path)
    
    def get_file_url(self, file: File, expires_in: int = 3600) -> str:
        """Get a URL for the file."""
        if file.is_public and file.file_url:
            return file.file_url
        return self.provider.get_url(file.file_path, expires_in)
    
    @transaction.atomic
    def delete_file(self, file: File, permanent: bool = False) -> bool:
        """Delete a file (soft or permanent)."""
        if permanent:
            # Delete from storage
            self.provider.delete(file.file_path)
            
            # Delete thumbnails
            for size, url in file.thumbnails.items():
                thumb_path = file.file_path.replace(
                    f'.{file.file_extension}',
                    f'_thumb_{size}.{file.file_extension}'
                )
                self.provider.delete(thumb_path)
            
            # Update usage
            usage, _ = StorageUsage.objects.get_or_create(tenant=self.tenant)
            usage.total_files = max(0, usage.total_files - 1)
            usage.total_size_bytes = max(0, usage.total_size_bytes - file.file_size)
            
            if file.is_image:
                usage.image_count = max(0, usage.image_count - 1)
                usage.image_size_bytes = max(0, usage.image_size_bytes - file.file_size)
            else:
                usage.other_count = max(0, usage.other_count - 1)
                usage.other_size_bytes = max(0, usage.other_size_bytes - file.file_size)
            
            usage.save()
            file.delete()
        else:
            # Soft delete
            file.is_deleted = True
            file.deleted_at = timezone.now()
            file.save()
        
        return True
    
    # ============= FOLDERS =============
    
    def create_folder(
        self,
        name: str,
        parent: Folder = None,
        owner_id: str = '',
        owner_type: str = 'user',
        is_public: bool = False
    ) -> Folder:
        """Create a folder."""
        return Folder.objects.create(
            tenant=self.tenant,
            name=name,
            parent=parent,
            owner_id=owner_id,
            owner_type=owner_type,
            is_public=is_public
        )
    
    def get_folder(self, folder_id: str) -> Optional[Folder]:
        """Get a folder by ID."""
        try:
            return Folder.objects.get(id=folder_id, tenant=self.tenant)
        except Folder.DoesNotExist:
            return None
    
    def list_folder(self, folder: Folder = None) -> Dict:
        """List contents of a folder."""
        if folder:
            folders = folder.children.all()
            files = folder.files.filter(is_deleted=False)
        else:
            folders = Folder.objects.filter(tenant=self.tenant, parent=None)
            files = File.objects.filter(
                tenant=self.tenant,
                folder=None,
                is_deleted=False
            )
        
        return {
            'folders': list(folders),
            'files': list(files),
            'current_folder': folder
        }
    
    def delete_folder(self, folder: Folder, recursive: bool = False) -> bool:
        """Delete a folder."""
        if not recursive and (folder.children.exists() or folder.files.filter(is_deleted=False).exists()):
            raise ValueError("Folder is not empty. Use recursive=True to delete contents.")
        
        if recursive:
            # Delete all files
            for file in folder.files.all():
                self.delete_file(file, permanent=True)
            
            # Delete all subfolders
            for child in folder.children.all():
                self.delete_folder(child, recursive=True)
        
        folder.delete()
        return True
    
    # ============= USAGE =============
    
    def get_usage(self) -> StorageUsage:
        """Get storage usage for tenant."""
        usage, _ = StorageUsage.objects.get_or_create(tenant=self.tenant)
        return usage
    
    def recalculate_usage(self) -> StorageUsage:
        """Recalculate storage usage."""
        usage, _ = StorageUsage.objects.get_or_create(tenant=self.tenant)
        usage.recalculate()
        return usage






