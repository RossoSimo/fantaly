from django.db import models

from players.models import Player, Position, Team
from seasons.models import Season


class PlayerSeasonStats(models.Model):
    """Statistics for one player in one season.

    Uniquely keyed on (player, season) so refreshing the *current* season's
    numbers never touches a previous season's row (see AGENTS.md > Player
    Data — "Do not overwrite historical statistics when new information
    arrives").
    """

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='season_stats')
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='player_stats')

    # Snapshot of context that can change season to season.
    club = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    position = models.CharField(max_length=3, choices=Position.choices)

    appearances = models.PositiveSmallIntegerField(default=0)
    starts = models.PositiveSmallIntegerField(default=0)
    minutes = models.PositiveIntegerField(default=0)
    goals = models.PositiveSmallIntegerField(default=0)
    assists = models.PositiveSmallIntegerField(default=0)
    yellow_cards = models.PositiveSmallIntegerField(default=0)
    red_cards = models.PositiveSmallIntegerField(default=0)
    own_goals = models.PositiveSmallIntegerField(default=0)
    clean_sheets = models.PositiveSmallIntegerField(null=True, blank=True)
    matches_missed = models.PositiveSmallIntegerField(default=0)

    fantasy_points = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    average_rating = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    fantasy_average = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'player season stats'
        constraints = [
            models.UniqueConstraint(fields=['player', 'season'], name='unique_stats_per_player_season'),
        ]
        indexes = [models.Index(fields=['season', 'position'])]

    def __str__(self):
        return f"{self.player} — {self.season}"


class PlayerStatusValue(models.TextChoices):
    STARTING = 'starting', 'Starting'
    BENCH = 'bench', 'Bench'
    INJURED = 'injured', 'Injured'
    SUSPENDED = 'suspended', 'Suspended'
    DOUBTFUL = 'doubtful', 'Doubtful'
    UNAVAILABLE = 'unavailable', 'Unavailable'
    RETURNING = 'returning', 'Returning from injury'
    UNKNOWN = 'unknown', 'Unknown'


class PlayerStatus(models.Model):
    """A status signal for a player at a point in time.

    Append-only by design: each new signal is a new row rather than an
    overwrite, which gives a full history and lets callers distinguish
    confirmed information from predictions (see AGENTS.md > Player
    Status). Use `PlayerStatus.objects.current_for(player, season)` to get
    the latest signal.
    """

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='statuses')
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='player_statuses')
    status = models.CharField(max_length=15, choices=PlayerStatusValue.choices)
    source = models.CharField(max_length=100, blank=True)
    is_confirmed = models.BooleanField(
        default=True,
        help_text="False if this is a prediction/rumor rather than confirmed information.",
    )
    confidence = models.FloatField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'player statuses'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['player', 'season', '-created_at'])]

    def __str__(self):
        return f"{self.player} — {self.get_status_display()} ({self.created_at:%Y-%m-%d})"

    @classmethod
    def current_for(cls, player, season):
        return cls.objects.filter(player=player, season=season).order_by('-created_at').first()
