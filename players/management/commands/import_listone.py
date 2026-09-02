"""manage.py import_listone <path> --season "2026/2027"

Imports fantacalcio.it's official player listone: upserts Player records
(via the identity resolution service) and records each player's official
quotation as an ESTIMATED market price observation for the given season.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from providers.market.fantacalcio_it import import_listone_prices
from providers.players.fantacalcio_it import import_players, parse_listone
from seasons.models import Season


class Command(BaseCommand):
    help = "Import players and official quotations from a fantacalcio.it listone .xlsx file."

    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help='Path to the listone .xlsx file')
        parser.add_argument('--season', required=True, help='Season label, e.g. "2026/2027"')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Parse and report what would happen without writing to the database.',
        )

    def handle(self, path, season, dry_run, **options):
        try:
            season_obj = Season.objects.get(label=season)
        except Season.DoesNotExist:
            raise CommandError(
                f"No season with label '{season}'. Create it first (e.g. via /admin/)."
            )

        rows = parse_listone(path)
        self.stdout.write(f"Parsed {len(rows)} rows from {path}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes written."))
            return

        with transaction.atomic():
            player_summary = import_players(rows)
            price_summary = import_listone_prices(rows, season_obj, player_summary.player_by_external_id)

        self.stdout.write(self.style.SUCCESS(
            f"Players: {player_summary.created} created, {player_summary.updated} updated, "
            f"{player_summary.ambiguous} ambiguous (needs manual review — see PlayerIdentityMatchLog in /admin/)."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Prices: {price_summary.created} created, {price_summary.updated} updated, "
            f"{price_summary.skipped_no_player} skipped (no resolved player)."
        ))