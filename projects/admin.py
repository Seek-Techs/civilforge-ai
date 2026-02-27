from django.contrib import admin
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'status', 'location', 'created_at', 'updated_at', 'has_boq')
    list_filter = ('status', 'created_at', 'owner')
    search_fields = ('name', 'description', 'owner__username', 'location')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'boq_generated_at')

    @admin.display(boolean=True, description='BOQ Generated')
    def has_boq(self, obj):
        return obj.boq_result is not None

    def save_model(self, request, obj, form, change):
        if not change:
            obj._request_user = request.user
        super().save_model(request, obj, form, change)

    fieldsets = (
        (None, {
            'fields': ('owner', 'name', 'description', 'status', 'location', 'notes')
        }),
        ('BOQ', {
            'fields': ('boq_result', 'boq_generated_at'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
