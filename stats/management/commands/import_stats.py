"""manage.py import_stats <path> --season "2025/2026"

Imports a fantacalcio.it statistics workbook into PlayerSeasonStats for
the given season. Players must already exist (typically via import_listone)
and be mapped by fantacalcio.it Id — unmatched rows are skipped, never
turned into new Player records.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from providers.stats.fantacalcio_it import import_season_stats, parse_stats_workbook
from seasons.models import Season


class Command(BaseCommand):
    help = "Import season statistics from a fantacalcio.it stats .xlsx file."

    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help='Path to the statistics .xlsx file')
        parser.add_argument('--season', required=True, help='Season label the numbers belong to, e.g. "2025/2026"')
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

        rows = parse_stats_workbook(path)
        self.stdout.write(f"Parsed {len(rows)} rows from {path}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes written."))
            return

        with transaction.atomic():
            summary = import_season_stats(rows, season_obj)

        self.stdout.write(self.style.SUCCESS(
            f"Stats: {summary.created} created, {summary.updated} updated, "
            f"{summary.unmatched} unmatched (no fantacalcio.it player id — import the listone first)."
        ))
