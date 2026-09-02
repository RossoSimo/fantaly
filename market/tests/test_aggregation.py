from datetime import date
from decimal import Decimal

from django.test import TestCase

from market.aggregation import get_market_summary
from market.models import MarketPriceObservation, PriceType
from testing_utils import make_player, make_season


class MarketAggregationTests(TestCase):
    def setUp(self):
        self.player = make_player('Market Subject')
        self.season = make_season()

    def test_summary_only_uses_observed_prices(self):
        MarketPriceObservation.objects.create(
            player=self.player, season=self.season, price=Decimal('20'),
            price_type=PriceType.OBSERVED, observed_at=date(2026, 8, 1),
        )
        MarketPriceObservation.objects.create(
            player=self.player, season=self.season, price=Decimal('30'),
            price_type=PriceType.OBSERVED, observed_at=date(2026, 8, 2),
        )
        # An estimate that must never influence the "market price".
        MarketPriceObservation.objects.create(
            player=self.player, season=self.season, price=Decimal('1000'),
            price_type=PriceType.ESTIMATED, observed_at=date(2026, 8, 3),
        )

        summary = get_market_summary(self.player, self.season)
        self.assertEqual(summary.observation_count, 2)
        self.assertEqual(summary.average, 25.0)
        self.assertEqual(summary.minimum, 20.0)
        self.assertEqual(summary.maximum, 30.0)

    def test_summary_with_no_observed_prices_is_empty(self):
        MarketPriceObservation.objects.create(
            player=self.player, season=self.season, price=Decimal('99'),
            price_type=PriceType.USER_ENTERED, observed_at=date(2026, 8, 1),
        )
        summary = get_market_summary(self.player, self.season)
        self.assertEqual(summary.observation_count, 0)
        self.assertIsNone(summary.average)
