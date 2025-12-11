from django.contrib import admin
from .models import Project, GeneratedModel, GeneratedAPI, ProjectVersion


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'status', 'created_at', 'deployed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'deployed_at']


@admin.register(GeneratedModel)
class GeneratedModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'project__name']


@admin.register(GeneratedAPI)
class GeneratedAPIAdmin(admin.ModelAdmin):
    list_display = ['method', 'path', 'project', 'created_at']
    list_filter = ['method', 'created_at']
    search_fields = ['path', 'project__name']


@admin.register(ProjectVersion)
class ProjectVersionAdmin(admin.ModelAdmin):
    list_display = ['project', 'version', 'created_at']
    list_filter = ['created_at']
    search_fields = ['project__name', 'version']

