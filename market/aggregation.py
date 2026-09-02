"""Market price aggregation.

Deliberately excludes anything that isn't PriceType.OBSERVED, so an
estimate or a system valuation can never leak into what's presented as
"the market price" (see AGENTS.md > Italian Market Data).
"""

from dataclasses import dataclass
from statistics import median

from .models import MarketPriceObservation, PriceType


@dataclass
class MarketSummary:
    average: float | None
    median: float | None
    minimum: float | None
    maximum: float | None
    observation_count: int
    recent_prices: list


def get_market_summary(player, season, recent_limit: int = 5) -> MarketSummary:
    observations = MarketPriceObservation.objects.filter(
        player=player, season=season, price_type=PriceType.OBSERVED,
    ).order_by('-observed_at')

    prices = [float(p) for p in observations.values_list('price', flat=True)]
    if not prices:
        return MarketSummary(None, None, None, None, 0, [])

    return MarketSummary(
        average=sum(prices) / len(prices),
        median=median(prices),
        minimum=min(prices),
        maximum=max(prices),
        observation_count=len(prices),
        recent_prices=prices[:recent_limit],
    )
