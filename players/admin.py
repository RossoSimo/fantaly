from django.contrib import admin

from .models import Player, PlayerAlias, PlayerExternalId, PlayerIdentityMatchLog, Team


class PlayerAliasInline(admin.TabularInline):
    model = PlayerAlias
    extra = 1


class PlayerExternalIdInline(admin.TabularInline):
    model = PlayerExternalId
    extra = 1


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'full_name', 'position', 'club', 'is_active')
    list_filter = ('position', 'is_active', 'club')
    search_fields = ('full_name', 'display_name', 'aliases__alias')
    inlines = [PlayerAliasInline, PlayerExternalIdInline]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'external_id')
    search_fields = ('name', 'short_name')


@admin.register(PlayerIdentityMatchLog)
class PlayerIdentityMatchLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'player', 'match_method', 'confidence', 'is_ambiguous')
    list_filter = ('match_method', 'is_ambiguous')
    readonly_fields = [f.name for f in PlayerIdentityMatchLog._meta.fields]

    def has_add_permission(self, request):
        # Log entries are only ever created by the matching service.
        return False
