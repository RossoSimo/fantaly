from django.contrib import admin

from .models import Season


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('label', 'year_start', 'year_end', 'is_current')
    list_filter = ('is_current',)
    ordering = ('-year_start',)
