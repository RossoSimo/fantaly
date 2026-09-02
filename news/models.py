from django.db import models

from players.models import Player, Team


class NewsSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    feed_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class NewsCategory(models.TextChoices):
    INJURY = 'injury', 'Injury'
    SUSPENSION = 'suspension', 'Suspension'
    LINEUP = 'lineup', 'Line-up'
    TRANSFER = 'transfer', 'Transfer'
    TRAINING = 'training', 'Training'
    PERFORMANCE = 'performance', 'Performance'
    COACH_STATEMENT = 'coach_statement', 'Coach statement'
    GENERAL = 'general', 'General news'


class PlayerNews(models.Model):
    """A single news item, optionally tied to a player and/or club.

    Deduplication prefers a stable `external_id` from the source when
    available; otherwise a normalized (source, title, published_at) triple
    is used as the fallback key (see AGENTS.md > News and RSS and
    invariant-adjacent "same news item must not be imported multiple
    times"). See news/ingestion.py for the import service that enforces
    this.
    """

    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, null=True, blank=True, related_name='news_items',
    )
    club = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='news_items',
    )
    source = models.ForeignKey(NewsSource, on_delete=models.SET_NULL, null=True, blank=True)

    title = models.CharField(max_length=300)
    summary = models.TextField(blank=True)
    url = models.URLField()
    external_id = models.CharField(max_length=200, blank=True, null=True)
    category = models.CharField(max_length=20, choices=NewsCategory.choices, default=NewsCategory.GENERAL)

    published_at = models.DateTimeField(null=True, blank=True)
    retrieved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'player news'
        ordering = ['-published_at', '-retrieved_at']
        constraints = [
            models.UniqueConstraint(
                fields=['source', 'external_id'],
                name='unique_news_external_id_per_source',
                condition=models.Q(external_id__isnull=False),
            ),
        ]
        indexes = [
            models.Index(fields=['player', '-published_at']),
            models.Index(fields=['source', 'title', 'published_at']),
        ]

    def __str__(self):
        return self.title
