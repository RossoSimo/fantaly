from django.contrib import admin

from .models import PlayerSeasonStats, PlayerStatus


@admin.register(PlayerSeasonStats)
class PlayerSeasonStatsAdmin(admin.ModelAdmin):
    list_display = ('player', 'season', 'appearances', 'goals', 'assists', 'fantasy_average', 'updated_at')
    list_filter = ('season', 'position')
    search_fields = ('player__display_name', 'player__full_name')


@admin.register(PlayerStatus)
class PlayerStatusAdmin(admin.ModelAdmin):
    list_display = ('player', 'season', 'status', 'is_confirmed', 'created_at')
    list_filter = ('season', 'status', 'is_confirmed')
    search_fields = ('player__display_name',)
