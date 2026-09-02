"""Small factory helpers shared across test suites.

Not a Django app — just plain functions, imported directly by test
modules that need a quick, consistent way to build a Season/League/
Player/FantasyManager graph without repeating boilerplate everywhere.
"""

from django.contrib.auth import get_user_model

from leagues.models import FantasyManager, League, LeagueMembership, LeagueRole
from players.models import Player, Position, Team
from seasons.models import Season

User = get_user_model()


def make_user(username='owner', **kwargs):
    return User.objects.create_user(username=username, password='testpass123', **kwargs)


def make_season(label=None, year_start=2026, **kwargs):
    if label is None:
        # Unique per call by default so tests that don't care about a
        # shared season can call this repeatedly without label clashes.
        import uuid
        label = f"{year_start}/{year_start + 1}-{uuid.uuid4().hex[:6]}"
    return Season.objects.create(label=label, year_start=year_start, year_end=year_start + 1, **kwargs)


def make_league(owner=None, season=None, **kwargs):
    owner = owner or make_user()
    season = season or make_season()
    defaults = dict(name='Test League', owner=owner, season=season, initial_credits=500, squad_size=25)
    defaults.update(kwargs)
    league = League.objects.create(**defaults)
    LeagueMembership.objects.create(league=league, user=owner, role=LeagueRole.OWNER)
    return league


def make_manager(league, name='Manager 1', **kwargs):
    return FantasyManager.objects.create(league=league, name=name, **kwargs)


def make_team(name='Napoli'):
    return Team.objects.get_or_create(name=name)[0]


def make_player(display_name='Test Player', position=Position.MIDFIELDER, club=None, **kwargs):
    return Player.objects.create(
        full_name=display_name, display_name=display_name, position=position,
        club=club or make_team(), **kwargs,
    )
