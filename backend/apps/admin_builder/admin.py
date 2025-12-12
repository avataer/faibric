from django.contrib import admin
from .models import (
    AdminBuilderConfig, AdminPage, Widget, DataSource,
    AdminTemplate, ExportedAdmin
)


@admin.register(AdminBuilderConfig)
class AdminBuilderConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'admin_name', 'theme', 'is_enabled']
    list_filter = ['theme', 'is_enabled']


class WidgetInline(admin.TabularInline):
    model = Widget
    extra = 0
    fields = ['name', 'widget_type', 'is_visible']


@admin.register(AdminPage)
class AdminPageAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'slug', 'page_type', 'is_published', 'nav_order']
    list_filter = ['page_type', 'is_published', 'show_in_nav']
    search_fields = ['name', 'title', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [WidgetInline]


@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'page', 'widget_type', 'is_visible']
    list_filter = ['widget_type', 'is_visible']
    search_fields = ['name']


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'source_type', 'cache_enabled']
    list_filter = ['source_type', 'cache_enabled']
    search_fields = ['name']


@admin.register(AdminTemplate)
class AdminTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_premium', 'is_active']
    list_filter = ['category', 'is_premium', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ExportedAdmin)
class ExportedAdminAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'version', 'build_status', 'created_at']
    list_filter = ['build_status', 'framework']
    readonly_fields = ['build_log']









