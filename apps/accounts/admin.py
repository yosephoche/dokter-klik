from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'role', 'clinic', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'clinic']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Access', {'fields': ('role', 'clinic', 'is_active', 'is_staff', 'is_superuser')}),
        ('MFA', {'fields': ('mfa_enabled',)}),
        ('Timestamps', {'fields': ('last_active', 'created_at', 'updated_at')}),
    )
    readonly_fields = ['created_at', 'updated_at', 'last_active']
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'clinic'),
        }),
    )
