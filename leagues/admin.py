from django.contrib import admin

from .models import FantasyManager, League, LeagueMembership


class LeagueMembershipInline(admin.TabularInline):
    model = LeagueMembership
    extra = 1


class FantasyManagerInline(admin.TabularInline):
    model = FantasyManager
    extra = 1


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name', 'season', 'owner', 'num_managers', 'initial_credits', 'is_active')
    list_filter = ('season', 'is_active')
    search_fields = ('name', 'owner__username')
    inlines = [LeagueMembershipInline, FantasyManagerInline]


@admin.register(FantasyManager)
class FantasyManagerAdmin(admin.ModelAdmin):
    list_display = ('name', 'league', 'user')
    list_filter = ('league',)
