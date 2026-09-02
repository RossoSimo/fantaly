from django.contrib import admin

from .models import PlayerValuation, ValuationComponent


class ValuationComponentInline(admin.TabularInline):
    model = ValuationComponent
    extra = 0


@admin.register(PlayerValuation)
class PlayerValuationAdmin(admin.ModelAdmin):
    list_display = ('player', 'league', 'season', 'suggested_price', 'engine_version', 'calculated_at')
    list_filter = ('league', 'season', 'engine_version')
    search_fields = ('player__display_name',)
    inlines = [ValuationComponentInline]
