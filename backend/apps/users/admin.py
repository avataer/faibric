from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'max_apps', 'created_at']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'created_at']
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('bio', 'avatar', 'max_apps')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('email', 'bio', 'max_apps')}),
    )

