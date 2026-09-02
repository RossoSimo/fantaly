from django.core.exceptions import ValidationError
from django.db import models


class Season(models.Model):
    """A single football season, e.g. 2026/2027.

    Every season-specific piece of domain data (statistics, statuses,
    valuations, market prices, auction transactions, roster entries) links
    to a Season so that data never bleeds across seasons and a player is
    never duplicated when a new season starts (see AGENTS.md > Season
    Management).
    """

    label = models.CharField(
        max_length=20,
        unique=True,
        help_text="Display label, e.g. '2026/2027'.",
    )
    year_start = models.PositiveSmallIntegerField()
    year_end = models.PositiveSmallIntegerField()
    is_current = models.BooleanField(
        default=False,
        help_text="Only one season should be marked current at a time.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year_start']

    def __str__(self):
        return self.label

    def clean(self):
        if self.year_end != self.year_start + 1:
            raise ValidationError(
                {'year_end': "year_end must be exactly one year after year_start."}
            )

    def save(self, *args, **kwargs):
        # Enforce "only one current season" at the model layer so every
        # entry point (admin, management commands, views) gets the same
        # guarantee rather than relying on callers to remember.
        if self.is_current:
            Season.objects.exclude(pk=self.pk).filter(is_current=True).update(
                is_current=False
            )
        super().save(*args, **kwargs)
