from rest_framework import serializers
from .models import Template


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = [
            'id', 'name', 'slug', 'description', 'category',
            'schema_template', 'api_template', 'ui_template',
            'thumbnail', 'usage_count', 'created_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at']


class TemplateListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list view"""
    class Meta:
        model = Template
        fields = [
            'id', 'name', 'slug', 'description', 'category',
            'thumbnail', 'usage_count'
        ]

