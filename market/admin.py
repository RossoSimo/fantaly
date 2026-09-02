from django.contrib import admin

from .models import MarketPriceObservation


@admin.register(MarketPriceObservation)
class MarketPriceObservationAdmin(admin.ModelAdmin):
    list_display = ('player', 'season', 'price', 'price_type', 'observed_at', 'is_anonymized')
    list_filter = ('season', 'price_type', 'is_anonymized')
    search_fields = ('player__display_name',)
