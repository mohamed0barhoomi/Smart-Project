from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class UtilisateurAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("username", "email")

    fieldsets = UserAdmin.fieldsets + (
        ("SMART PROJECT", {"fields": ("role",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("SMART PROJECT", {"fields": ("email", "role")}),
    )