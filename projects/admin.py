from django.contrib import admin
from .models import Project

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at', 'update_at')     # columns shown in list
    list_filter = ('created_at', 'owner')                           # filter sidebar
    search_fields = ('name', 'description', 'owner__username')                 # search box
    date_hierarchy = 'created_at'                           # date navigation
    readonly_fields = ('created_at', 'update_at')          # can't edit timestamps

    def save_model(self, request, obj, form, change):
        if not change:  # new object
            obj._request_user = request.user  # temporary attribute
        super().save_model(request, obj, form, change)

    fieldsets = (
        (None, {
            'fields': ('owner','name', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'update_at'),
            'classes': ('collapse',)                        # collapsed by default
        }),
    )