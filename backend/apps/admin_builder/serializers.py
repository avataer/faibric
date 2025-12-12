from rest_framework import serializers
from .models import (
    AdminBuilderConfig, AdminPage, Widget, DataSource,
    AdminTemplate, ExportedAdmin
)


class AdminBuilderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminBuilderConfig
        fields = [
            'id', 'admin_name', 'logo_url', 'favicon_url',
            'primary_color', 'secondary_color', 'theme',
            'allow_custom_css', 'allow_custom_js',
            'custom_css', 'custom_head_html',
            'is_enabled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = [
            'id', 'name', 'widget_type', 'config', 'style',
            'data_source', 'data_query',
            'is_visible', 'visibility_conditions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WidgetCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = [
            'name', 'widget_type', 'config', 'style',
            'data_source', 'data_query',
            'is_visible', 'visibility_conditions'
        ]


class AdminPageSerializer(serializers.ModelSerializer):
    widgets = WidgetSerializer(many=True, read_only=True)
    
    class Meta:
        model = AdminPage
        fields = [
            'id', 'name', 'slug', 'title', 'description', 'icon',
            'parent', 'layout', 'page_type', 'data_source',
            'show_in_nav', 'nav_order',
            'requires_auth', 'allowed_roles',
            'is_published', 'published_at',
            'widgets',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'published_at', 'created_at', 'updated_at']


class AdminPageListSerializer(serializers.ModelSerializer):
    widget_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AdminPage
        fields = [
            'id', 'name', 'slug', 'title', 'icon',
            'page_type', 'show_in_nav', 'nav_order',
            'is_published', 'widget_count'
        ]
    
    def get_widget_count(self, obj):
        return obj.widgets.count()


class AdminPageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminPage
        fields = [
            'name', 'slug', 'title', 'description', 'icon',
            'parent', 'layout', 'page_type', 'data_source',
            'show_in_nav', 'nav_order',
            'requires_auth', 'allowed_roles'
        ]


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = [
            'id', 'name', 'source_type', 'config',
            'cache_enabled', 'cache_ttl_seconds', 'transform',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DataSourceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = [
            'name', 'source_type', 'config',
            'cache_enabled', 'cache_ttl_seconds', 'transform'
        ]


class AdminTemplateSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    thumbnail_url = serializers.CharField(allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField())
    features = serializers.ListField(child=serializers.CharField())
    theme = serializers.DictField()
    is_premium = serializers.BooleanField(default=False)


class ApplyTemplateSerializer(serializers.Serializer):
    template_slug = serializers.CharField()


class ExportedAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportedAdmin
        fields = [
            'id', 'name', 'version', 'framework',
            'build_status', 'download_url',
            'created_at'
        ]
        read_only_fields = ['id', 'build_status', 'download_url', 'created_at']


class ExportRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)


# Widget type catalog
WIDGET_TYPES = [
    {'type': 'chart_bar', 'name': 'Bar Chart', 'icon': '📊', 'category': 'charts'},
    {'type': 'chart_line', 'name': 'Line Chart', 'icon': '📈', 'category': 'charts'},
    {'type': 'chart_pie', 'name': 'Pie Chart', 'icon': '🥧', 'category': 'charts'},
    {'type': 'chart_area', 'name': 'Area Chart', 'icon': '📉', 'category': 'charts'},
    {'type': 'stat_card', 'name': 'Stat Card', 'icon': '🔢', 'category': 'data'},
    {'type': 'table', 'name': 'Data Table', 'icon': '📋', 'category': 'data'},
    {'type': 'form', 'name': 'Form', 'icon': '📝', 'category': 'input'},
    {'type': 'text', 'name': 'Text/HTML', 'icon': '📄', 'category': 'content'},
    {'type': 'image', 'name': 'Image', 'icon': '🖼️', 'category': 'content'},
    {'type': 'button', 'name': 'Button', 'icon': '🔘', 'category': 'input'},
    {'type': 'card', 'name': 'Card', 'icon': '🃏', 'category': 'layout'},
    {'type': 'list', 'name': 'List', 'icon': '📑', 'category': 'data'},
    {'type': 'calendar', 'name': 'Calendar', 'icon': '📅', 'category': 'data'},
    {'type': 'map', 'name': 'Map', 'icon': '🗺️', 'category': 'data'},
    {'type': 'video', 'name': 'Video', 'icon': '🎬', 'category': 'content'},
    {'type': 'iframe', 'name': 'IFrame', 'icon': '🌐', 'category': 'content'},
    {'type': 'divider', 'name': 'Divider', 'icon': '➖', 'category': 'layout'},
    {'type': 'spacer', 'name': 'Spacer', 'icon': '⬜', 'category': 'layout'},
    {'type': 'tabs', 'name': 'Tabs', 'icon': '📂', 'category': 'layout'},
    {'type': 'accordion', 'name': 'Accordion', 'icon': '📚', 'category': 'layout'},
    {'type': 'modal', 'name': 'Modal Trigger', 'icon': '🪟', 'category': 'layout'},
    {'type': 'custom', 'name': 'Custom Component', 'icon': '⚙️', 'category': 'advanced'},
]









