from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from market.models import MarketPriceObservation, PriceType
from players.models import Player, PlayerExternalId, Position
from providers.players.fantacalcio_it import PROVIDER
from stats.models import PlayerSeasonStats
from testing_utils import make_player, make_season, make_team, make_user


def _write_stats_xlsx(path: Path, rows, headers=None, title='Statistiche Fantacalcio'):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Tutti'
    ws.append([title])
    ws.append(headers or ['Id', 'R', 'Nome', 'Squadra', 'Pv', 'Mv', 'Fm', 'Gf', 'Ass', 'Amm', 'Esp', 'Au'])
    for row in rows:
        ws.append(row)
    wb.save(path)


class PlayerListStatsViewTests(TestCase):
    def setUp(self):
        self.user = make_user('searcher')
        self.client.force_login(self.user)
        self.previous = make_season(label='2025/2026', year_start=2025)
        self.current = make_season(label='2026/2027', year_start=2026, is_current=True)
        self.napoli = make_team('Napoli')
        self.roma = make_team('Roma')
        self.mario = make_player('Mario Rossi', position=Position.MIDFIELDER, club=self.napoli)
        self.luca = make_player('Luca Bianchi', position=Position.FORWARD, club=self.roma)
        PlayerSeasonStats.objects.create(
            player=self.mario, season=self.previous, position=Position.MIDFIELDER,
            club=self.napoli, appearances=34, goals=8, assists=6,
            average_rating=Decimal('6.50'), fantasy_average=Decimal('7.20'),
        )
        PlayerSeasonStats.objects.create(
            player=self.luca, season=self.previous, position=Position.FORWARD,
            club=self.roma, appearances=20, goals=12, assists=3,
            average_rating=Decimal('6.80'), fantasy_average=Decimal('8.10'),
        )
        MarketPriceObservation.objects.create(
            player=self.mario, season=self.current, price=Decimal('25'),
            price_type=PriceType.ESTIMATED, source='fantacalcio.it listone',
            observed_at=date(2026, 8, 1),
        )

    def test_search_filters_by_name(self):
        response = self.client.get(reverse('players:list'), {'q': 'Mario'})
        self.assertContains(response, 'Mario Rossi')
        self.assertNotContains(response, 'Luca Bianchi')

    def test_search_filters_by_club(self):
        response = self.client.get(reverse('players:list'), {'q': 'Roma'})
        self.assertContains(response, 'Luca Bianchi')
        self.assertNotContains(response, 'Mario Rossi')

    def test_filter_by_position(self):
        response = self.client.get(reverse('players:list'), {'position': Position.FORWARD})
        self.assertContains(response, 'Luca Bianchi')
        self.assertNotContains(response, 'Mario Rossi')

    def test_filter_by_club_id(self):
        response = self.client.get(reverse('players:list'), {'club': str(self.roma.pk)})
        self.assertContains(response, 'Luca Bianchi')
        self.assertNotContains(response, 'Mario Rossi')

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('players:list'))
        self.assertEqual(response.status_code, 302)

    def test_defaults_to_previous_season_stats(self):
        response = self.client.get(reverse('players:list'))
        self.assertContains(response, 'Showing statistics for <strong>2025/2026</strong>')
        self.assertContains(response, '7,20')
        self.assertContains(response, '8,10')

    def test_can_switch_stats_season(self):
        PlayerSeasonStats.objects.create(
            player=self.mario, season=self.current, position=Position.MIDFIELDER,
            appearances=2, goals=1, fantasy_average=Decimal('6.00'),
        )
        response = self.client.get(reverse('players:list'), {'season': '2026/2027'})
        self.assertContains(response, '6,00')
        self.assertNotContains(response, '7,20')

    def test_shows_estimated_quotation_without_calling_it_market(self):
        response = self.client.get(reverse('players:list'))
        self.assertContains(response, '25')
        self.assertContains(response, 'not an observed auction price')

    def test_inactive_players_are_hidden_by_default(self):
        self.luca.is_active = False
        self.luca.save()
        response = self.client.get(reverse('players:list'))
        self.assertNotContains(response, 'Luca Bianchi')
        response = self.client.get(reverse('players:list'), {'active': '0'})
        self.assertContains(response, 'Luca Bianchi')
        self.assertNotContains(response, 'Mario Rossi')


class PlayerDetailStatsTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.season = make_season(label='2025/2026', year_start=2025, is_current=True)
        self.player = make_player('Mario Rossi', position=Position.MIDFIELDER)
        PlayerSeasonStats.objects.create(
            player=self.player, season=self.season, position=Position.MIDFIELDER,
            appearances=34, starts=30, minutes=2700, goals=8, assists=6,
            yellow_cards=4, red_cards=0, own_goals=0,
            fantasy_points=Decimal('210.50'),
            average_rating=Decimal('6.50'), fantasy_average=Decimal('7.20'),
        )

    def test_detail_shows_full_season_stats(self):
        response = self.client.get(reverse('players:detail', kwargs={'pk': self.player.pk}))
        self.assertContains(response, 'Mario Rossi')
        self.assertContains(response, '2025/2026')
        self.assertContains(response, '2700')
        self.assertContains(response, '210,50')
        self.assertContains(response, '7,20')

    def test_detail_does_not_present_estimates_as_observed_market(self):
        MarketPriceObservation.objects.create(
            player=self.player, season=self.season, price=Decimal('25'),
            price_type=PriceType.ESTIMATED, source='fantacalcio.it listone',
            observed_at=date(2026, 8, 1),
        )
        response = self.client.get(reverse('players:detail', kwargs={'pk': self.player.pk}))
        self.assertContains(response, 'Estimated quotation')
        self.assertContains(response, 'No observed auction prices yet')


class PlayerCreateViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_can_create_a_player(self):
        response = self.client.post(reverse('players:create'), {
            'full_name': 'New Player', 'display_name': 'New Player',
            'first_name': 'New', 'last_name': 'Player',
            'position': Position.DEFENDER, 'is_active': 'on',
        })
        self.assertEqual(Player.objects.filter(display_name='New Player').count(), 1)
        self.assertEqual(response.status_code, 302)


class FantacalcioStatsImportTests(TestCase):
    def setUp(self):
        self.season = make_season(label='2025/2026', year_start=2025)
        self.player = make_player('Svilar', position=Position.GOALKEEPER)
        PlayerExternalId.objects.create(
            player=self.player, provider=PROVIDER, external_id='5841',
        )

    def test_import_attaches_stats_to_existing_player_by_external_id(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'stats.xlsx'
            _write_stats_xlsx(path, [
                [5841, 'P', 'Svilar', 'Roma', 36, 6.32, 5.10, 0, 0, 1, 0, 0],
            ])
            call_command('import_stats', str(path), season='2025/2026')

        stats = PlayerSeasonStats.objects.get(player=self.player, season=self.season)
        self.assertEqual(stats.appearances, 36)
        self.assertEqual(stats.average_rating, Decimal('6.32'))
        self.assertEqual(stats.fantasy_average, Decimal('5.10'))
        self.assertEqual(stats.club.name, 'Roma')

    def test_import_does_not_create_a_player_when_id_is_unknown(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'stats.xlsx'
            _write_stats_xlsx(path, [
                [9999, 'A', 'Ghost', 'Napoli', 10, 6.00, 6.50, 3, 1, 0, 0, 0],
            ])
            call_command('import_stats', str(path), season='2025/2026')

        self.assertFalse(Player.objects.filter(display_name='Ghost').exists())
        self.assertEqual(PlayerSeasonStats.objects.count(), 0)

    def test_refreshing_one_season_never_rewrites_another(self):
        older = make_season(label='2024/2025', year_start=2024)
        PlayerSeasonStats.objects.create(
            player=self.player, season=older, position=Position.GOALKEEPER,
            appearances=30, fantasy_average=Decimal('5.00'),
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'stats.xlsx'
            _write_stats_xlsx(path, [
                [5841, 'P', 'Svilar', 'Roma', 36, 6.32, 5.10, 0, 0, 1, 0, 0],
            ])
            call_command('import_stats', str(path), season='2025/2026')

        older_row = PlayerSeasonStats.objects.get(player=self.player, season=older)
        self.assertEqual(older_row.appearances, 30)
        self.assertEqual(older_row.fantasy_average, Decimal('5.00'))
