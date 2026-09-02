"""Imports fantacalcio.it listone quotations as price observations.

The listone's `Qt.A` is fantacalcio.it's own official pre-season
quotation — nobody actually paid it in an auction, so it must never be
recorded as PriceType.OBSERVED (see AGENTS.md > Italian Market Data:
"Never present an estimate as an observed market price"). It goes in as
PriceType.ESTIMATED instead.
"""

from dataclasses import dataclass
from datetime import date

from market.models import MarketPriceObservation, PriceType
from providers.players.fantacalcio_it import ListoneRow

SOURCE_LABEL = 'fantacalcio.it listone'


@dataclass
class PriceImportSummary:
    created: int = 0
    updated: int = 0
    skipped_no_player: int = 0


def import_listone_prices(rows: list[ListoneRow], season, player_by_external_id: dict) -> PriceImportSummary:
    """Record each row's classic quotation as today's ESTIMATED price for
    that player/season. Safe to re-run: re-running the same day updates
    that day's snapshot rather than duplicating it; running on a later
    date adds a new snapshot, which is what you want for a price trend
    over time.
    """
    summary = PriceImportSummary()
    today = date.today()

    for row in rows:
        if row.is_departed:
            # A departed player's old quotation isn't a live price signal.
            continue
        player = player_by_external_id.get(row.external_id)
        if player is None:
            summary.skipped_no_player += 1
            continue

        _, created = MarketPriceObservation.objects.update_or_create(
            player=player, season=season, source=SOURCE_LABEL, observed_at=today,
            defaults={'price': row.classic_price, 'price_type': PriceType.ESTIMATED, 'is_anonymized': True},
        )
        if created:
            summary.created += 1
        else:
            summary.updated += 1

    return summary