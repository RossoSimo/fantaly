from django.contrib import admin

from .models import NewsSource, PlayerNews


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'feed_url', 'is_active')


@admin.register(PlayerNews)
class PlayerNewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'player', 'club', 'category', 'published_at', 'source')
    list_filter = ('category', 'source')
    search_fields = ('title', 'player__display_name')
