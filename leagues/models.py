from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from seasons.models import Season


class League(models.Model):
    """A fantasy football league, fully isolated from every other league.

    League-specific settings (budget, squad composition, bid limits, ...)
    must never be assumed to apply elsewhere — see AGENTS.md > Multi-League
    Support and invariant #8. A league is scoped to a single Season; running
    the same group of friends' league again next year means creating a new
    League row for the new season.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_leagues',
    )
    name = models.CharField(max_length=100)
    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name='leagues')

    # Squad / budget configuration
    num_managers = models.PositiveSmallIntegerField(default=8)
    initial_credits = models.PositiveIntegerField(default=500)
    squad_size = models.PositiveSmallIntegerField(default=25)
    slots_goalkeepers = models.PositiveSmallIntegerField(default=3)
    slots_defenders = models.PositiveSmallIntegerField(default=8)
    slots_midfielders = models.PositiveSmallIntegerField(default=8)
    slots_forwards = models.PositiveSmallIntegerField(default=6)

    # Auction configuration
    min_bid = models.PositiveIntegerField(default=1)
    max_bid = models.PositiveIntegerField(null=True, blank=True)
    allow_overspend = models.BooleanField(
        default=False,
        help_text="If disabled (default), a manager cannot bid more credits than they have left.",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name', 'season'], name='unique_league_per_owner_season'),
        ]

    def __str__(self):
        return f"{self.name} ({self.season})"

    def clean(self):
        total_position_slots = (
            self.slots_goalkeepers + self.slots_defenders
            + self.slots_midfielders + self.slots_forwards
        )
        if total_position_slots > self.squad_size:
            raise ValidationError(
                "Position slots (%d) cannot exceed squad_size (%d)."
                % (total_position_slots, self.squad_size)
            )
        if self.max_bid is not None and self.max_bid < self.min_bid:
            raise ValidationError({'max_bid': "max_bid cannot be lower than min_bid."})


class LeagueRole(models.TextChoices):
    OWNER = 'owner', 'Owner'
    MANAGER = 'manager', 'Manager'
    VIEWER = 'viewer', 'Viewer'


class LeagueMembership(models.Model):
    """Grants a user access to a league. League membership is explicit —
    a user has no access to a league's private data without one of these
    rows (see AGENTS.md > Authentication and Authorization)."""

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='league_memberships')
    role = models.CharField(max_length=10, choices=LeagueRole.choices, default=LeagueRole.VIEWER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['league', 'user'], name='unique_membership_per_user_league'),
        ]

    def __str__(self):
        return f"{self.user} @ {self.league} ({self.role})"


class FantasyManager(models.Model):
    """A participant in a league's auction and standings.

    Deliberately decoupled from User: during a live auction, one person
    often tracks budgets for friends who never log into the app
    themselves (see AGENTS.md > Authentication and Authorization — "the
    core auction tracker should work for ordinary participants").
    `user` is set only when that manager also has an account.
    """

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='managers')
    name = models.CharField(max_length=100)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fantasy_manager_profiles',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['league', 'name'], name='unique_manager_name_per_league'),
        ]

    def __str__(self):
        return f"{self.name} ({self.league})"
