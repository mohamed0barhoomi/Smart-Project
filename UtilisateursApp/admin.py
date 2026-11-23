from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class UtilisateurAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("username", "email", "company_name")

    fieldsets = UserAdmin.fieldsets + (
        ("SMART PROJECT", {"fields": ("role", "company_name", "company_description", "company_skills")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("SMART PROJECT", {"fields": ("email", "role")}),
    )