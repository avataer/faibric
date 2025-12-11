"""
Serializers for projects app
"""
from rest_framework import serializers
from .models import Project, GeneratedModel, GeneratedAPI, ProjectVersion


class GeneratedModelSerializer(serializers.ModelSerializer):
    """Serializer for GeneratedModel"""
    class Meta:
        model = GeneratedModel
        fields = ['id', 'name', 'fields', 'relationships', 'created_at']


class GeneratedAPISerializer(serializers.ModelSerializer):
    """Serializer for GeneratedAPI"""
    class Meta:
        model = GeneratedAPI
        fields = ['id', 'path', 'method', 'handler_code', 'description', 'created_at']


class ProjectVersionSerializer(serializers.ModelSerializer):
    """Serializer for ProjectVersion"""
    class Meta:
        model = ProjectVersion
        fields = ['id', 'version', 'snapshot', 'notes', 'created_at']


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project with nested generated code"""
    user = serializers.StringRelatedField(read_only=True)
    models = GeneratedModelSerializer(many=True, read_only=True, source='generatedmodel_set')
    apis = GeneratedAPISerializer(many=True, read_only=True, source='generatedapi_set')
    
    class Meta:
        model = Project
        fields = [
            'id', 'user', 'name', 'description', 'status', 'template',
            'user_prompt', 'ai_analysis', 'database_schema', 'api_code',
            'frontend_code', 'subdomain', 'deployment_url', 'container_id',
            'models', 'apis', 'created_at', 'updated_at', 'deployed_at'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'ai_analysis', 'database_schema',
            'api_code', 'frontend_code', 'subdomain', 'deployment_url',
            'container_id', 'created_at', 'updated_at', 'deployed_at'
        ]


class ProjectListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views"""
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'user', 'name', 'description', 'status',
            'deployment_url', 'created_at', 'updated_at'
        ]


class ProjectCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new project"""
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'user_prompt', 'template', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']


