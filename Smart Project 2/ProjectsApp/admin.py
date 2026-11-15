from django.contrib import admin
from .models import Project
# Register your models here.

admin.site.site_header = "Smart UML"
admin.site.site_title = "Smart UML"
admin.site.index_title = "Administration"


class adminProject(admin.ModelAdmin):
    list_display = ('title', 'status', 'user', 'created_at', 'updated_at')
    list_filter = ('status', "created_at", "updated_at")
    search_fields = ('title', 'description')
    list_editable = ('status',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Informations générales', {
            'fields': (
                'title',
                'description',
                'status',
                'user',
            )
        }),

        ('Diagrammes UML', {
            'fields': (
                'class_diagram',
                'use_case_diagram',
                'diagram_history',
            )
        }),

        ('Exigences', {
            'fields': ('requirements',)
        }),

        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


admin.site.register(Project, adminProject)
