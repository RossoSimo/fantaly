from django.test import TestCase

from seasons.models import Season


class SeasonTests(TestCase):
    def test_only_one_season_can_be_current(self):
        first = Season.objects.create(label='2025/2026', year_start=2025, year_end=2026, is_current=True)
        second = Season.objects.create(label='2026/2027', year_start=2026, year_end=2027, is_current=True)

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(first.is_current)
        self.assertTrue(second.is_current)

    def test_year_end_must_follow_year_start(self):
        season = Season(label='Broken', year_start=2025, year_end=2030)
        with self.assertRaises(Exception):
            season.full_clean()
