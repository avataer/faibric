"""
Admin interface for Code Library management.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    LibraryCategory, LibraryItem, LibraryItemUsage, LibraryVersion,
    AdminDesignRules, CustomerMessage, Constraint, ResearchCache
)


@admin.register(LibraryCategory)
class LibraryCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'order', 'item_count']
    list_editable = ['order']
    search_fields = ['name']
    
    def item_count(self, obj):
        return obj.libraryitem_set.count()
    item_count.short_description = 'Items'


@admin.register(LibraryItem)
class LibraryItemAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'item_type', 'category', 'quality_badge', 
        'usage_count', 'is_approved', 'is_active', 'created_by'
    ]
    list_filter = ['item_type', 'is_active', 'is_approved', 'created_by', 'category']
    search_fields = ['name', 'description', 'keywords']
    list_editable = ['is_approved', 'is_active']
    readonly_fields = ['usage_count', 'last_used_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'item_type', 'category')
        }),
        ('Code', {
            'fields': ('code', 'language'),
            'classes': ('wide',)
        }),
        ('Search & Matching', {
            'fields': ('keywords', 'tags')
        }),
        ('Quality & Curation', {
            'fields': ('quality_score', 'is_approved', 'is_active', 'is_public')
        }),
        ('Usage Stats', {
            'fields': ('usage_count', 'last_used_at', 'source_project', 'created_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def quality_badge(self, obj):
        score = obj.quality_score
        if score >= 0.8:
            color = '#22c55e'
            label = 'High'
        elif score >= 0.5:
            color = '#f59e0b'
            label = 'Medium'
        else:
            color = '#ef4444'
            label = 'Low'
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; '
            'border-radius:4px; font-size:11px;">{} ({:.0%})</span>',
            color, label, score
        )
    quality_badge.short_description = 'Quality'


@admin.register(LibraryItemUsage)
class LibraryItemUsageAdmin(admin.ModelAdmin):
    list_display = ['item', 'project', 'usage_type', 'was_helpful', 'created_at']
    list_filter = ['usage_type', 'was_helpful', 'created_at']
    search_fields = ['item__name', 'project__name']
    readonly_fields = ['created_at']


@admin.register(AdminDesignRules)
class AdminDesignRulesAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'updated_at']
    list_filter = ['is_active']
    
    fieldsets = (
        ('Status', {
            'fields': ('name', 'is_active')
        }),
        ('Typography', {
            'fields': ('font_rules',),
            'classes': ('wide',)
        }),
        ('Colors', {
            'fields': ('color_rules',),
            'classes': ('wide',)
        }),
        ('Layout', {
            'fields': ('layout_rules',),
            'classes': ('wide',)
        }),
        ('Components', {
            'fields': ('component_rules',),
            'classes': ('wide',)
        }),
        ('Forbidden Patterns', {
            'fields': ('forbidden_patterns',),
            'classes': ('wide',)
        }),
        ('Quality Standards', {
            'fields': ('quality_standards',),
            'classes': ('wide',)
        }),
        ('Custom Rules', {
            'fields': ('custom_rules',),
            'classes': ('wide',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        # If activating this ruleset, deactivate others
        if obj.is_active:
            AdminDesignRules.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)


@admin.register(CustomerMessage)
class CustomerMessageAdmin(admin.ModelAdmin):
    list_display = ['operation_key', 'customer_message', 'min_display_seconds', 'is_active']
    list_filter = ['is_active']
    list_editable = ['customer_message', 'is_active']
    search_fields = ['operation_key', 'customer_message']


@admin.register(Constraint)
class ConstraintAdmin(admin.ModelAdmin):
    list_display = ['name', 'constraint_type', 'priority', 'is_active']
    list_filter = ['constraint_type', 'is_active']
    list_editable = ['is_active', 'priority']
    search_fields = ['name', 'description', 'rule_text']


@admin.register(LibraryVersion)
class LibraryVersionAdmin(admin.ModelAdmin):
    list_display = ['item', 'version_number', 'created_by', 'created_at']
    list_filter = ['created_by']
    search_fields = ['item__name']
    readonly_fields = ['created_at']


@admin.register(ResearchCache)
class ResearchCacheAdmin(admin.ModelAdmin):
    list_display = ['query_short', 'source', 'expires_at', 'created_at']
    list_filter = ['source']
    search_fields = ['query']
    readonly_fields = ['query_hash', 'created_at']
    
    def query_short(self, obj):
        return obj.query[:50] + '...' if len(obj.query) > 50 else obj.query
    query_short.short_description = 'Query'
