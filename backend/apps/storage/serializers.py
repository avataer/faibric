from rest_framework import serializers
from .models import StorageConfig, Folder, File, StorageUsage


class StorageConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageConfig
        fields = [
            'id', 'provider', 'max_file_size_mb', 'max_storage_gb',
            'allowed_image_types', 'allowed_file_types',
            'auto_optimize_images', 'max_image_dimension', 'jpeg_quality',
            'generate_thumbnails', 'thumbnail_sizes',
            'is_enabled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StorageConfigUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageConfig
        fields = [
            'provider', 'bucket_name', 'access_key', 'secret_key',
            'region', 'endpoint_url', 'cdn_url',
            'max_file_size_mb', 'max_storage_gb',
            'allowed_image_types', 'allowed_file_types',
            'auto_optimize_images', 'max_image_dimension', 'jpeg_quality',
            'generate_thumbnails', 'thumbnail_sizes',
            'is_enabled'
        ]
        extra_kwargs = {
            'access_key': {'write_only': True},
            'secret_key': {'write_only': True},
        }


class FolderSerializer(serializers.ModelSerializer):
    path = serializers.CharField(read_only=True)
    file_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'parent', 'path',
            'owner_id', 'owner_type', 'is_public',
            'file_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FolderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ['name', 'parent', 'owner_id', 'owner_type', 'is_public']


class FileSerializer(serializers.ModelSerializer):
    size_formatted = serializers.CharField(read_only=True)
    folder_path = serializers.SerializerMethodField()
    
    class Meta:
        model = File
        fields = [
            'id', 'folder', 'folder_path',
            'original_name', 'file_url',
            'content_type', 'file_size', 'size_formatted', 'file_extension',
            'is_image', 'image_width', 'image_height', 'thumbnails',
            'owner_id', 'owner_type', 'is_public',
            'download_count', 'last_accessed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'original_name', 'file_url', 'content_type', 'file_size',
            'file_extension', 'is_image', 'image_width', 'image_height',
            'thumbnails', 'download_count', 'last_accessed_at',
            'created_at', 'updated_at'
        ]
    
    def get_folder_path(self, obj):
        return obj.folder.path if obj.folder else '/'


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    folder_id = serializers.UUIDField(required=False, allow_null=True)
    is_public = serializers.BooleanField(default=False)


class StorageUsageSerializer(serializers.ModelSerializer):
    total_size_formatted = serializers.CharField(read_only=True)
    usage_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = StorageUsage
        fields = [
            'total_files', 'total_size_bytes', 'total_size_formatted',
            'image_count', 'image_size_bytes',
            'document_count', 'document_size_bytes',
            'other_count', 'other_size_bytes',
            'usage_percentage', 'last_calculated_at'
        ]
    
    def get_usage_percentage(self, obj):
        config = obj.tenant.storage_config
        if not config:
            return 0
        max_bytes = config.max_storage_gb * 1024 * 1024 * 1024
        if max_bytes == 0:
            return 0
        return round(obj.total_size_bytes / max_bytes * 100, 2)


# Public API serializers

class PublicFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    folder_id = serializers.UUIDField(required=False, allow_null=True)


class PublicFileListSerializer(serializers.Serializer):
    folder_id = serializers.UUIDField(required=False, allow_null=True)
    owner_id = serializers.CharField(max_length=255, required=False)







