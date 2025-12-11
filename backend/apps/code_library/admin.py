"""
Django admin configuration for code library.
"""
from django.contrib import admin

from .models import (
    LibraryCategory,
    LibraryItem,
    LibraryVersion,
    LibraryItemUsage,
    Constraint,
    ResearchCache,
)


@admin.register(LibraryCategory)
class LibraryCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'icon', 'created_at']
    list_filter = ['parent']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


class LibraryVersionInline(admin.TabularInline):
    model = LibraryVersion
    extra = 0
    readonly_fields = ['created_at']


@admin.register(LibraryItem)
class LibraryItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'item_type', 'language', 'quality_score', 'usage_count', 'is_active', 'is_public']
    list_filter = ['item_type', 'language', 'is_active', 'is_public', 'source']
    search_fields = ['name', 'description', 'keywords']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['usage_count', 'last_used_at', 'created_at', 'updated_at']
    inlines = [LibraryVersionInline]
    
    fieldsets = [
        (None, {
            'fields': ['tenant', 'name', 'slug', 'item_type', 'category']
        }),
        ('Code', {
            'fields': ['language', 'code', 'description', 'usage_example', 'documentation']
        }),
        ('Metadata', {
            'fields': ['keywords', 'tags', 'dependencies']
        }),
        ('Quality', {
            'fields': ['quality_score', 'usage_count', 'last_used_at']
        }),
        ('Source', {
            'fields': ['source', 'source_url', 'created_by']
        }),
        ('Status', {
            'fields': ['is_active', 'is_public', 'is_deprecated', 'deprecation_note']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(LibraryVersion)
class LibraryVersionAdmin(admin.ModelAdmin):
    list_display = ['item', 'version', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['item__name', 'version', 'changelog']
    readonly_fields = ['created_at']


@admin.register(LibraryItemUsage)
class LibraryItemUsageAdmin(admin.ModelAdmin):
    list_display = ['item', 'project', 'usage_type', 'was_helpful', 'created_at']
    list_filter = ['usage_type', 'was_helpful', 'created_at']
    search_fields = ['item__name', 'project__name']
    readonly_fields = ['created_at']


@admin.register(Constraint)
class ConstraintAdmin(admin.ModelAdmin):
    list_display = ['name', 'constraint_type', 'priority', 'is_active', 'created_at']
    list_filter = ['constraint_type', 'is_active']
    search_fields = ['name', 'content']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ResearchCache)
class ResearchCacheAdmin(admin.ModelAdmin):
    list_display = ['query', 'research_type', 'result_count', 'expires_at', 'created_at']
    list_filter = ['research_type', 'created_at']
    search_fields = ['query']
    readonly_fields = ['query_hash', 'created_at']






