from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase
from openpyxl import Workbook

from players.models import Player, PlayerExternalId, Position
from providers.players.fantacalcio_it import PROVIDER
from testing_utils import make_player, make_season


def _write_listone_xlsx(path: Path, active_rows, departed_rows=None):
    wb = Workbook()
    tutti = wb.active
    tutti.title = 'Tutti'
    tutti.append(['Quotazioni Fantacalcio'])
    tutti.append(['Id', 'R', 'RM', 'Nome', 'Squadra', 'Qt.A', 'Qt.I', 'Diff.', 'Qt.A M', 'Qt.I M', 'Diff.M', 'FVM', 'FVM M'])
    for row in active_rows:
        tutti.append(row)
    ceduti = wb.create_sheet('Ceduti')
    ceduti.append(['Calciatori Ceduti'])
    ceduti.append(['Id', 'R', 'RM', 'Nome', 'Squadra', 'Qt.A', 'Qt.I', 'Diff.', 'Qt.A M', 'Qt.I M', 'Diff.M', 'FVM', 'FVM M'])
    for row in departed_rows or []:
        ceduti.append(row)
    wb.save(path)


class ListoneImportTests(TestCase):
    def setUp(self):
        self.season = make_season(label='2026/2027', year_start=2026, is_current=True)

    def test_import_creates_player_and_external_id(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'listone.xlsx'
            _write_listone_xlsx(path, [
                [5841, 'P', 'Por', 'Svilar', 'Roma', 19, 18, 1, 19, 18, 1, 85, 85],
            ])
            call_command('import_listone', str(path), season='2026/2027')

        player = Player.objects.get(display_name='Svilar')
        self.assertEqual(player.position, Position.GOALKEEPER)
        self.assertEqual(player.club.name, 'Roma')
        self.assertTrue(
            PlayerExternalId.objects.filter(
                player=player, provider=PROVIDER, external_id='5841',
            ).exists()
        )

    def test_reimport_updates_the_same_player_instead_of_duplicating(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'listone.xlsx'
            _write_listone_xlsx(path, [
                [5841, 'P', 'Por', 'Svilar', 'Roma', 19, 18, 1, 19, 18, 1, 85, 85],
            ])
            call_command('import_listone', str(path), season='2026/2027')
            _write_listone_xlsx(path, [
                [5841, 'P', 'Por', 'Svilar', 'Inter', 21, 19, 2, 21, 19, 2, 90, 90],
            ])
            call_command('import_listone', str(path), season='2026/2027')

        self.assertEqual(Player.objects.filter(display_name='Svilar').count(), 1)
        player = Player.objects.get(display_name='Svilar')
        self.assertEqual(player.club.name, 'Inter')
