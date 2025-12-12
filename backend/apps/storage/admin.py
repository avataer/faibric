from django.contrib import admin
from .models import StorageConfig, Folder, File, StorageUsage


@admin.register(StorageConfig)
class StorageConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'provider', 'max_file_size_mb', 'max_storage_gb', 'is_enabled']
    list_filter = ['provider', 'is_enabled']


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'parent', 'owner_id', 'is_public', 'created_at']
    list_filter = ['is_public', 'owner_type']
    search_fields = ['name', 'owner_id']


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'tenant', 'content_type', 'size_formatted', 'is_image', 'is_public', 'created_at']
    list_filter = ['is_image', 'is_public', 'is_deleted', 'content_type']
    search_fields = ['original_name', 'owner_id']
    readonly_fields = ['stored_name', 'file_path', 'md5_hash', 'sha256_hash']


@admin.register(StorageUsage)
class StorageUsageAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'total_files', 'total_size_formatted', 'last_calculated_at']
    readonly_fields = ['total_files', 'total_size_bytes', 'image_count', 'document_count']









