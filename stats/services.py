"""Season-scoped player statistics.

Callers must always pass an explicit Season. Updating one season's row
never touches another season's row (see AGENTS.md > Player Data).
"""

from seasons.models import Season
from stats.models import PlayerSeasonStats

STATS_FIELDS = (
    'appearances',
    'starts',
    'minutes',
    'goals',
    'assists',
    'yellow_cards',
    'red_cards',
    'own_goals',
    'clean_sheets',
    'matches_missed',
    'fantasy_points',
    'average_rating',
    'fantasy_average',
)


def upsert_player_season_stats(*, player, season, club=None, position, **stat_fields) -> tuple[PlayerSeasonStats, bool]:
    """Create or refresh the stats row for exactly one (player, season)."""
    defaults = {'club': club, 'position': position}
    for field in STATS_FIELDS:
        if field in stat_fields:
            defaults[field] = stat_fields[field]
    return PlayerSeasonStats.objects.update_or_create(
        player=player,
        season=season,
        defaults=defaults,
    )


def current_season() -> Season | None:
    return Season.objects.filter(is_current=True).first()


def previous_season(season: Season | None) -> Season | None:
    if season is None:
        return None
    return (
        Season.objects.filter(year_start__lt=season.year_start)
        .order_by('-year_start')
        .first()
    )


def default_stats_season() -> Season | None:
    """Season whose numbers are most useful on the player list.

    During auction prep the current season is usually empty, so we prefer
    the previous season when one exists.
    """
    current = current_season()
    return previous_season(current) or current or Season.objects.order_by('-year_start').first()
