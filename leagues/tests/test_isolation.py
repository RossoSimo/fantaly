from django.test import TestCase

from leagues.models import League, LeagueMembership
from testing_utils import make_league, make_manager, make_player, make_season, make_user


class LeagueIsolationTests(TestCase):
    def test_league_settings_do_not_leak_across_leagues(self):
        season = make_season()
        league_a = make_league(name='League A', season=season, initial_credits=500)
        league_b = make_league(name='League B', season=season, initial_credits=250, owner=make_user('owner2'))

        self.assertEqual(League.objects.get(pk=league_a.pk).initial_credits, 500)
        self.assertEqual(League.objects.get(pk=league_b.pk).initial_credits, 250)

    def test_manager_names_can_repeat_across_leagues_but_not_within_one(self):
        season = make_season()
        league_a = make_league(name='League A', season=season)
        league_b = make_league(name='League B', season=season, owner=make_user('owner2'))

        make_manager(league_a, name='Same Name')
        # Same manager name in a different league is fine — leagues are isolated.
        make_manager(league_b, name='Same Name')

        with self.assertRaises(Exception):
            make_manager(league_a, name='Same Name')

    def test_a_user_only_sees_leagues_they_are_a_member_of(self):
        season = make_season()
        owner1 = make_user('owner1')
        owner2 = make_user('owner2')
        league_a = make_league(name='League A', owner=owner1, season=season)
        make_league(name='League B', owner=owner2, season=season)

        visible = League.objects.filter(memberships__user=owner1)
        self.assertEqual(list(visible), [league_a])

    def test_max_bid_cannot_be_lower_than_min_bid(self):
        league = League(
            owner=make_user(), name='Bad League', season=make_season(),
            min_bid=10, max_bid=5,
        )
        with self.assertRaises(Exception):
            league.full_clean()

    def test_position_slots_cannot_exceed_squad_size(self):
        league = League(
            owner=make_user(), name='Overcommitted', season=make_season(),
            squad_size=5, slots_goalkeepers=3, slots_defenders=3, slots_midfielders=3, slots_forwards=3,
        )
        with self.assertRaises(Exception):
            league.full_clean()
