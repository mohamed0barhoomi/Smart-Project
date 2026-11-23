from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["projet", "role", "modele", "created_at"]
    list_filter = ["role"]
