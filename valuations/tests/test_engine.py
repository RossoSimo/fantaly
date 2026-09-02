from decimal import Decimal

from django.test import TestCase

from players.models import Position
from stats.models import PlayerSeasonStats, PlayerStatus, PlayerStatusValue
from testing_utils import make_league, make_player, make_season
from valuations.engine import calculate_valuation
from valuations.models import PlayerValuation


class ValuationEngineTests(TestCase):
    def setUp(self):
        self.last_season = make_season(label='2025/2026', year_start=2025)
        self.this_season = make_season(label='2026/2027', year_start=2026)
        self.league = make_league(season=self.this_season, initial_credits=500)
        self.player = make_player('Valued Player', position=Position.FORWARD)

    def test_valuation_is_explained_by_its_components(self):
        PlayerSeasonStats.objects.create(
            player=self.player, season=self.last_season, position=Position.FORWARD,
            appearances=30, fantasy_average=Decimal('7.50'),
        )

        valuation = calculate_valuation(self.player, self.league, self.this_season)

        self.assertGreater(valuation.suggested_price, 0)
        component_sum = sum(c.amount for c in valuation.components.all())
        self.assertEqual(valuation.suggested_price, max(component_sum, Decimal('1')))
        self.assertGreaterEqual(valuation.components.count(), 1)

    def test_injury_status_reduces_the_suggested_price(self):
        PlayerSeasonStats.objects.create(
            player=self.player, season=self.last_season, position=Position.FORWARD,
            appearances=30, fantasy_average=Decimal('7.50'),
        )
        healthy_valuation = calculate_valuation(self.player, self.league, self.this_season)

        PlayerStatus.objects.create(player=self.player, season=self.this_season, status=PlayerStatusValue.INJURED)
        injured_valuation = calculate_valuation(self.player, self.league, self.this_season)

        self.assertLess(injured_valuation.suggested_price, healthy_valuation.suggested_price)

    def test_recalculating_replaces_the_previous_valuation_rather_than_duplicating(self):
        calculate_valuation(self.player, self.league, self.this_season)
        calculate_valuation(self.player, self.league, self.this_season)
        self.assertEqual(
            PlayerValuation.objects.filter(player=self.player, league=self.league, season=self.this_season).count(),
            1,
        )
