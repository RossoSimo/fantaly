from django.contrib import admin

from .models import Auction, AuctionNomination, AuctionTransaction, Bid, PlayerAvailability


class NominationInline(admin.TabularInline):
    model = AuctionNomination
    extra = 0
    fields = ('player', 'status', 'current_bid', 'winning_manager')


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'league', 'status', 'started_at', 'completed_at')
    list_filter = ('league', 'status')
    inlines = [NominationInline]


@admin.register(AuctionTransaction)
class AuctionTransactionAdmin(admin.ModelAdmin):
    list_display = ('player', 'manager', 'league', 'price', 'is_correction', 'purchased_at')
    list_filter = ('league', 'is_correction')
    search_fields = ('player__display_name', 'manager__name')
    readonly_fields = ('purchased_at',)


@admin.register(PlayerAvailability)
class PlayerAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('player', 'league', 'status', 'updated_at')
    list_filter = ('league', 'status')
    search_fields = ('player__display_name',)


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('nomination', 'manager', 'amount', 'placed_at')
