from django.contrib import admin

from .models import Besoin


@admin.register(Besoin)
class BesoinAdmin(admin.ModelAdmin):
    list_display = ["titre", "projet", "type_besoin", "priorite", "source"]
    list_filter = ["type_besoin", "priorite", "source"]
    search_fields = ["titre"]
