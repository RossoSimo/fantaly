from django.db import models

from leagues.models import League
from players.models import Player
from seasons.models import Season


class PlayerValuation(models.Model):
    """The suggested auction price for a player within a specific league.

    Scoped per (player, league, season) because the same player can be
    worth very different amounts in leagues with different scoring and
    budget rules (see AGENTS.md > Multi-League Support). The breakdown of
    *why* is stored separately in ValuationComponent so the number is
    never an opaque magic value.
    """

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='valuations')
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='valuations')
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='valuations')
    suggested_price = models.DecimalField(max_digits=6, decimal_places=2)
    engine_version = models.CharField(
        max_length=50,
        help_text="Identifies which valuation algorithm produced this result.",
    )
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['player', 'league', 'season'],
                name='unique_valuation_per_player_league_season',
            ),
        ]
        indexes = [models.Index(fields=['league', 'season'])]

    def __str__(self):
        return f"{self.player} @ {self.league}: {self.suggested_price}"


class ValuationComponent(models.Model):
    """One line item explaining part of a PlayerValuation's suggested_price.

    Example: "Base value: 32", "Expected starting role: +5",
    "Injury risk: -3" (see AGENTS.md > Player Valuation).
    """

    valuation = models.ForeignKey(PlayerValuation, on_delete=models.CASCADE, related_name='components')
    label = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.label}: {self.amount:+}"
