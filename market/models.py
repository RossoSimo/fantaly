from django.db import models

from players.models import Player
from seasons.models import Season


class PriceType(models.TextChoices):
    OBSERVED = 'observed', 'Actual observed price'
    ESTIMATED = 'estimated', 'Estimated price'
    USER_ENTERED = 'user_entered', 'User-entered price'
    SYSTEM_VALUATION = 'system_valuation', 'System-generated valuation'


class MarketPriceObservation(models.Model):
    """A single price data point for a player, from any source.

    `price_type` must always be set correctly — an estimate must never be
    presented as an observed market price (see AGENTS.md > Italian Market
    Data). Aggregation for display (average/median/min/max) should be
    computed only over price_type=OBSERVED rows; see market/aggregation.py.
    """

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='market_prices')
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='market_prices')
    price = models.DecimalField(max_digits=6, decimal_places=2)
    price_type = models.CharField(max_length=20, choices=PriceType.choices)
    source = models.CharField(
        max_length=100, blank=True,
        help_text="Where this price observation came from, e.g. an aggregator name.",
    )
    is_anonymized = models.BooleanField(
        default=True,
        help_text="True unless the contributing manager explicitly consented to attribution.",
    )
    observed_at = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-observed_at']
        indexes = [models.Index(fields=['player', 'season', 'price_type'])]

    def __str__(self):
        return f"{self.player} — {self.price} ({self.get_price_type_display()}, {self.observed_at})"
