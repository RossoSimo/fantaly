"""Player valuation engine.

Designed so new algorithms can be added without touching callers (see
AGENTS.md > Player Valuation — "designed so that different algorithms can
be introduced later"). Callers should go through `calculate_valuation()`,
not instantiate an engine directly, so swapping the default engine is a
one-line change.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from stats.models import PlayerSeasonStats, PlayerStatus, PlayerStatusValue

from .models import PlayerValuation, ValuationComponent


@dataclass
class ValuationLineItem:
    label: str
    amount: Decimal


class ValuationEngine(ABC):
    """Interface every valuation algorithm must implement."""

    version: str

    @abstractmethod
    def compute(self, player, league, season) -> list[ValuationLineItem]:
        """Return an ordered list of line items; the sum is the suggested price."""
        raise NotImplementedError


class BaselineValuationEngine(ValuationEngine):
    """A simple, transparent starting-point engine.

    Base value comes from last season's fantasy average scaled by the
    league's budget; adjustments are applied for current-season form and
    injury/suspension risk. This is intentionally simple — it exists to
    give every league a reasonable, explainable starting price, not to be
    the final word on player value.
    """

    version = 'baseline-v1'

    # Scales a league's total budget against a fixed reference budget so
    # the same statistical player is priced sensibly across leagues with
    # very different initial_credits.
    REFERENCE_LEAGUE_BUDGET = Decimal('500')

    def compute(self, player, league, season) -> list[ValuationLineItem]:
        items = []
        budget_scale = Decimal(league.initial_credits) / self.REFERENCE_LEAGUE_BUDGET

        previous_season = (
            season.__class__.objects.filter(year_start__lt=season.year_start)
            .order_by('-year_start')
            .first()
        )
        base_value = Decimal('1')
        if previous_season is not None:
            prev_stats = PlayerSeasonStats.objects.filter(
                player=player, season=previous_season,
            ).first()
            if prev_stats and prev_stats.fantasy_average:
                base_value = (prev_stats.fantasy_average * Decimal('5')) * budget_scale
        base_value = max(base_value, Decimal('1'))
        items.append(ValuationLineItem('Base value (previous season)', base_value.quantize(Decimal('1'))))

        current_stats = PlayerSeasonStats.objects.filter(player=player, season=season).first()
        if current_stats and current_stats.appearances and current_stats.fantasy_average:
            form_adjustment = (current_stats.fantasy_average - Decimal('6')) * Decimal('2') * budget_scale
            if form_adjustment != 0:
                items.append(ValuationLineItem('Current-season form', form_adjustment.quantize(Decimal('1'))))

        latest_status = PlayerStatus.current_for(player, season)
        if latest_status and latest_status.status in (
            PlayerStatusValue.INJURED, PlayerStatusValue.SUSPENDED, PlayerStatusValue.DOUBTFUL,
        ):
            risk_penalty = (Decimal('-3') * budget_scale).quantize(Decimal('1'))
            items.append(ValuationLineItem(f"Risk: {latest_status.get_status_display()}", risk_penalty))

        return items


DEFAULT_ENGINE = BaselineValuationEngine()


@transaction.atomic
def calculate_valuation(player, league, season, engine: ValuationEngine | None = None) -> PlayerValuation:
    """Compute and persist a PlayerValuation, replacing any prior one for
    the same (player, league, season). Always keeps the breakdown so the
    result stays explainable."""
    engine = engine or DEFAULT_ENGINE
    line_items = engine.compute(player, league, season)
    suggested_price = sum((item.amount for item in line_items), Decimal('0'))
    # Never suggest a non-positive price.
    suggested_price = max(suggested_price, Decimal('1'))

    valuation, _ = PlayerValuation.objects.update_or_create(
        player=player, league=league, season=season,
        defaults={'suggested_price': suggested_price, 'engine_version': engine.version},
    )
    valuation.components.all().delete()
    ValuationComponent.objects.bulk_create([
        ValuationComponent(valuation=valuation, label=item.label, amount=item.amount, order=i)
        for i, item in enumerate(line_items)
    ])
    return valuation
