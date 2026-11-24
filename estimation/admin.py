from django.contrib import admin

from .models import Estimation, Projet


@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):
    list_display = ["nom", "proprietaire", "updated_at"]
    search_fields = ["nom"]


@admin.register(Estimation)
class EstimationAdmin(admin.ModelAdmin):
    list_display = ["projet", "cout", "delai", "updated_at"]
    search_fields = ["projet__nom"]
