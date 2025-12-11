import uuid
import os
from django.db import models
from django.utils import timezone


def get_upload_path(instance, filename):
    """Generate upload path: tenant_id/year/month/uuid_filename"""
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    now = timezone.now()
    return f"uploads/{instance.tenant.id}/{now.year}/{now.month:02d}/{unique_name}"


class StorageConfig(models.Model):
    """
    Storage configuration for a tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='storage_config'
    )
    
    # Storage provider
    provider = models.CharField(max_length=20, default='local', choices=[
        ('local', 'Local Storage'),
        ('s3', 'Amazon S3'),
        ('r2', 'Cloudflare R2'),
        ('gcs', 'Google Cloud Storage'),
    ])
    
    # S3/R2/GCS settings
    bucket_name = models.CharField(max_length=100, blank=True)
    access_key = models.CharField(max_length=200, blank=True)
    secret_key = models.CharField(max_length=200, blank=True)
    region = models.CharField(max_length=50, default='us-east-1')
    endpoint_url = models.URLField(blank=True)  # For R2 or custom S3
    
    # CDN settings
    cdn_url = models.URLField(blank=True)  # Custom CDN domain
    
    # Limits
    max_file_size_mb = models.PositiveIntegerField(default=50)
    max_storage_gb = models.PositiveIntegerField(default=10)
    
    # Allowed file types
    allowed_image_types = models.JSONField(
        default=list,
        blank=True,
        help_text="e.g., ['jpg', 'png', 'gif', 'webp']"
    )
    allowed_file_types = models.JSONField(
        default=list,
        blank=True,
        help_text="e.g., ['pdf', 'doc', 'docx', 'xlsx']"
    )
    
    # Image optimization
    auto_optimize_images = models.BooleanField(default=True)
    max_image_dimension = models.PositiveIntegerField(default=2048)
    jpeg_quality = models.PositiveIntegerField(default=85)
    generate_thumbnails = models.BooleanField(default=True)
    thumbnail_sizes = models.JSONField(
        default=list,
        blank=True,
        help_text="e.g., [150, 300, 600]"
    )
    
    # Status
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Storage config for {self.tenant.name}"
    
    def save(self, *args, **kwargs):
        if not self.allowed_image_types:
            self.allowed_image_types = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']
        if not self.allowed_file_types:
            self.allowed_file_types = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv', 'zip']
        if not self.thumbnail_sizes:
            self.thumbnail_sizes = [150, 300, 600]
        super().save(*args, **kwargs)


class Folder(models.Model):
    """
    Virtual folder for organizing files.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='storage_folders'
    )
    
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    
    # Owner (app user or system)
    owner_id = models.CharField(max_length=255, blank=True)
    owner_type = models.CharField(max_length=20, default='user', choices=[
        ('user', 'User'),
        ('app', 'Application'),
        ('system', 'System'),
    ])
    
    # Permissions
    is_public = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = [['tenant', 'parent', 'name']]
    
    def __str__(self):
        return self.name
    
    @property
    def path(self):
        """Get full path from root."""
        parts = [self.name]
        current = self.parent
        while current:
            parts.insert(0, current.name)
            current = current.parent
        return '/' + '/'.join(parts)
    
    @property
    def file_count(self):
        return self.files.filter(is_deleted=False).count()


class File(models.Model):
    """
    Uploaded file with metadata.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='storage_files'
    )
    folder = models.ForeignKey(
        Folder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='files'
    )
    
    # File info
    original_name = models.CharField(max_length=500)
    stored_name = models.CharField(max_length=500)  # Name on storage
    
    # File path/URL
    file_path = models.CharField(max_length=1000)  # Path in storage
    file_url = models.URLField(max_length=2000, blank=True)  # Public URL if available
    
    # File metadata
    content_type = models.CharField(max_length=100)
    file_size = models.BigIntegerField()  # In bytes
    file_extension = models.CharField(max_length=20)
    
    # Checksums
    md5_hash = models.CharField(max_length=32, blank=True)
    sha256_hash = models.CharField(max_length=64, blank=True)
    
    # Image-specific metadata
    is_image = models.BooleanField(default=False)
    image_width = models.PositiveIntegerField(null=True, blank=True)
    image_height = models.PositiveIntegerField(null=True, blank=True)
    
    # Thumbnails (for images)
    thumbnails = models.JSONField(default=dict, blank=True)
    # Format: {"150": "url", "300": "url", "600": "url"}
    
    # Owner
    owner_id = models.CharField(max_length=255, blank=True)
    owner_type = models.CharField(max_length=20, default='user', choices=[
        ('user', 'User'),
        ('app', 'Application'),
        ('system', 'System'),
    ])
    
    # Permissions
    is_public = models.BooleanField(default=False)
    
    # Access tracking
    download_count = models.PositiveIntegerField(default=0)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'folder', 'is_deleted']),
            models.Index(fields=['tenant', 'owner_id', 'is_deleted']),
            models.Index(fields=['tenant', 'content_type']),
        ]
    
    def __str__(self):
        return self.original_name
    
    @property
    def size_formatted(self):
        """Human-readable file size."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def increment_download(self):
        """Track file download."""
        self.download_count += 1
        self.last_accessed_at = timezone.now()
        self.save(update_fields=['download_count', 'last_accessed_at'])


class StorageUsage(models.Model):
    """
    Track storage usage per tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='storage_usage'
    )
    
    # Usage stats
    total_files = models.PositiveIntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)
    
    # By type
    image_count = models.PositiveIntegerField(default=0)
    image_size_bytes = models.BigIntegerField(default=0)
    
    document_count = models.PositiveIntegerField(default=0)
    document_size_bytes = models.BigIntegerField(default=0)
    
    other_count = models.PositiveIntegerField(default=0)
    other_size_bytes = models.BigIntegerField(default=0)
    
    last_calculated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Storage usage for {self.tenant.name}"
    
    @property
    def total_size_formatted(self):
        size = self.total_size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def recalculate(self):
        """Recalculate storage usage."""
        from django.db.models import Sum, Count
        
        files = File.objects.filter(tenant=self.tenant, is_deleted=False)
        
        # Total
        stats = files.aggregate(
            total=Count('id'),
            size=Sum('file_size')
        )
        self.total_files = stats['total'] or 0
        self.total_size_bytes = stats['size'] or 0
        
        # Images
        images = files.filter(is_image=True).aggregate(
            count=Count('id'),
            size=Sum('file_size')
        )
        self.image_count = images['count'] or 0
        self.image_size_bytes = images['size'] or 0
        
        # Documents
        doc_extensions = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv']
        docs = files.filter(file_extension__in=doc_extensions).aggregate(
            count=Count('id'),
            size=Sum('file_size')
        )
        self.document_count = docs['count'] or 0
        self.document_size_bytes = docs['size'] or 0
        
        # Other
        self.other_count = self.total_files - self.image_count - self.document_count
        self.other_size_bytes = self.total_size_bytes - self.image_size_bytes - self.document_size_bytes
        
        self.save()







