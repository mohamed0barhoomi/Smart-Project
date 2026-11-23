from django.contrib import admin

from .models import Diagramme


@admin.register(Diagramme)
class DiagrammeAdmin(admin.ModelAdmin):
    list_display = ["titre", "projet", "type_diagramme", "source", "updated_at"]
    list_filter = ["type_diagramme", "source"]
