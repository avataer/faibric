"""
Serializers for code library API.
"""
from rest_framework import serializers

from .models import (
    LibraryCategory,
    LibraryItem,
    LibraryVersion,
    LibraryItemUsage,
    Constraint,
    ResearchCache,
)


class LibraryCategorySerializer(serializers.ModelSerializer):
    """Serializer for library categories."""
    
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LibraryCategory
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'parent',
            'icon',
            'color',
            'item_count',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_item_count(self, obj):
        return obj.items.count()


class LibraryVersionSerializer(serializers.ModelSerializer):
    """Serializer for library item versions."""
    
    class Meta:
        model = LibraryVersion
        fields = [
            'id',
            'version',
            'code',
            'changelog',
            'dependencies',
            'created_by',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class LibraryItemSerializer(serializers.ModelSerializer):
    """Serializer for library items."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    version_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LibraryItem
        fields = [
            'id',
            'name',
            'slug',
            'item_type',
            'category',
            'category_name',
            'language',
            'code',
            'description',
            'usage_example',
            'documentation',
            'keywords',
            'tags',
            'dependencies',
            'quality_score',
            'usage_count',
            'last_used_at',
            'source',
            'source_url',
            'created_by',
            'is_active',
            'is_public',
            'is_deprecated',
            'deprecation_note',
            'version_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'usage_count', 'last_used_at', 'created_at', 'updated_at']
    
    def get_version_count(self, obj):
        return obj.versions.count()


class LibraryItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating library items."""
    
    class Meta:
        model = LibraryItem
        fields = [
            'name',
            'item_type',
            'category',
            'language',
            'code',
            'description',
            'usage_example',
            'documentation',
            'keywords',
            'tags',
            'dependencies',
            'source',
            'source_url',
            'is_public',
        ]


class LibraryItemDetailSerializer(LibraryItemSerializer):
    """Detailed serializer with versions."""
    
    versions = LibraryVersionSerializer(many=True, read_only=True)
    related_items = serializers.SerializerMethodField()
    
    class Meta(LibraryItemSerializer.Meta):
        fields = LibraryItemSerializer.Meta.fields + ['versions', 'related_items']
    
    def get_related_items(self, obj):
        from .search import LibrarySearchService
        
        service = LibrarySearchService(str(obj.tenant_id) if obj.tenant_id else None)
        related = service.get_related_items(str(obj.id), limit=5)
        
        return related


class ConstraintSerializer(serializers.ModelSerializer):
    """Serializer for constraints."""
    
    class Meta:
        model = Constraint
        fields = [
            'id',
            'name',
            'slug',
            'constraint_type',
            'content',
            'rules',
            'applies_to',
            'priority',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LibrarySearchSerializer(serializers.Serializer):
    """Serializer for search requests."""
    
    query = serializers.CharField()
    method = serializers.ChoiceField(
        choices=['hybrid', 'semantic', 'keyword'],
        default='hybrid'
    )
    item_type = serializers.CharField(required=False)
    language = serializers.CharField(required=False)
    category_id = serializers.UUIDField(required=False)
    limit = serializers.IntegerField(default=20, max_value=100)


class LibrarySearchResultSerializer(serializers.Serializer):
    """Serializer for search results."""
    
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    item_type = serializers.CharField()
    language = serializers.CharField()
    description = serializers.CharField()
    quality_score = serializers.FloatField()
    usage_count = serializers.IntegerField()
    keywords = serializers.ListField()
    similarity_score = serializers.FloatField(required=False)
    combined_score = serializers.FloatField(required=False)
    match_type = serializers.CharField(required=False)


class GenerateCodeRequestSerializer(serializers.Serializer):
    """Serializer for code generation requests."""
    
    description = serializers.CharField()
    language = serializers.ChoiceField(
        choices=['typescript', 'javascript', 'python', 'html', 'css'],
        default='typescript'
    )
    item_type = serializers.ChoiceField(
        choices=['component', 'service', 'utility', 'hook', 'api', 'model', 'snippet'],
        default='component'
    )
    search_library = serializers.BooleanField(default=True)
    do_research = serializers.BooleanField(default=True)
    apply_constraints = serializers.BooleanField(default=True)
    save_to_library = serializers.BooleanField(default=True)
    existing_code = serializers.CharField(required=False, allow_blank=True)


class GenerateCodeResponseSerializer(serializers.Serializer):
    """Serializer for code generation response."""
    
    success = serializers.BooleanField()
    code = serializers.CharField()
    from_library = serializers.BooleanField()
    library_item_id = serializers.UUIDField(required=False, allow_null=True)
    research_summary = serializers.CharField(required=False, allow_blank=True)
    constraints_applied = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    quality_score = serializers.FloatField()
    error = serializers.CharField(required=False, allow_null=True)


class ResearchRequestSerializer(serializers.Serializer):
    """Serializer for research requests."""
    
    topic = serializers.CharField()
    language = serializers.CharField(required=False)
    include_web = serializers.BooleanField(default=True)
    include_github = serializers.BooleanField(default=True)
    include_packages = serializers.BooleanField(default=True)







