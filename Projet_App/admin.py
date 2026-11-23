from django.contrib import admin

from .models import Projet


@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):
    list_display = ["nom", "proprietaire", "created_at", "updated_at"]
    search_fields = ["nom"]
