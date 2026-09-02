from decimal import Decimal

from django.test import TestCase

from players.models import Position
from seasons.models import Season
from stats.models import PlayerSeasonStats, PlayerStatus, PlayerStatusValue
from testing_utils import make_player, make_season


class PlayerSeasonStatsIsolationTests(TestCase):
    def test_updating_current_season_stats_never_touches_a_previous_season(self):
        player = make_player('Test Player', position=Position.MIDFIELDER)
        last_season = make_season(label='2025/2026', year_start=2025)
        this_season = make_season(label='2026/2027', year_start=2026)

        PlayerSeasonStats.objects.create(
            player=player, season=last_season, position=Position.MIDFIELDER,
            goals=10, fantasy_average=Decimal('7.00'),
        )
        PlayerSeasonStats.objects.create(
            player=player, season=this_season, position=Position.MIDFIELDER,
            goals=2, fantasy_average=Decimal('6.50'),
        )

        # Refresh "this season" as if new data arrived mid-season.
        current_row = PlayerSeasonStats.objects.get(player=player, season=this_season)
        current_row.goals = 5
        current_row.save()

        last_row = PlayerSeasonStats.objects.get(player=player, season=last_season)
        self.assertEqual(last_row.goals, 10)
        self.assertEqual(last_row.fantasy_average, Decimal('7.00'))

    def test_a_player_can_only_have_one_stats_row_per_season(self):
        player = make_player('Unique Stats', position=Position.FORWARD)
        season = make_season()
        PlayerSeasonStats.objects.create(player=player, season=season, position=Position.FORWARD)
        with self.assertRaises(Exception):
            PlayerSeasonStats.objects.create(player=player, season=season, position=Position.FORWARD)


class PlayerStatusHistoryTests(TestCase):
    def test_status_updates_are_appended_not_overwritten(self):
        player = make_player('Injury Prone', position=Position.DEFENDER)
        season = make_season()

        PlayerStatus.objects.create(player=player, season=season, status=PlayerStatusValue.STARTING)
        PlayerStatus.objects.create(player=player, season=season, status=PlayerStatusValue.INJURED)

        self.assertEqual(PlayerStatus.objects.filter(player=player, season=season).count(), 2)
        current = PlayerStatus.current_for(player, season)
        self.assertEqual(current.status, PlayerStatusValue.INJURED)
