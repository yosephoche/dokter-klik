"""Django admin registration for Clinic and DoctorSchedule."""

from django.contrib import admin

from apps.accounts.models import CustomUser

from .models import Clinic, DoctorSchedule


class UserInline(admin.TabularInline):
    model = CustomUser
    fk_name = "clinic"
    fields = ["email", "first_name", "last_name", "role", "is_active"]
    extra = 0
    can_delete = False
    show_change_link = True


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "phone",
        "subscription_plan",
        "is_active",
        "created_at",
    ]
    list_filter = ["subscription_plan", "is_active"]
    search_fields = ["name", "slug", "email"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]
    inlines = [UserInline]
    fieldsets = [
        (
            "Informasi Klinik",
            {
                "fields": [
                    "name",
                    "slug",
                    "address",
                    "phone",
                    "email",
                    "subscription_plan",
                    "is_active",
                ]
            },
        ),
        ("Billing", {"fields": ["consultation_fee"]}),
        # ('SATUSEHAT', {
        #     'fields': ['satusehat_org_id', 'satusehat_client_id', 'satusehat_client_secret'],
        #     'classes': ['collapse'],
        # }),
        # (
        #     "WhatsApp",
        #     {
        #         "fields": ["whatsapp_phone_number_id", "whatsapp_access_token"],
        #         "classes": ["collapse"],
        #     },
        # ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = [
        "clinic",
        "doctor",
        "day_of_week",
        "start_time",
        "end_time",
        "is_active",
    ]
    list_filter = ["clinic", "is_active"]
    search_fields = ["clinic__name", "doctor__email"]
