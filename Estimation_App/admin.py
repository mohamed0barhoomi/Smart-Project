from django.contrib import admin

from .models import Estimation


@admin.register(Estimation)
class EstimationAdmin(admin.ModelAdmin):
    list_display = ["projet", "cout", "delai", "updated_at"]
    search_fields = ["projet__nom"]
