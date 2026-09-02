from django.conf import settings
from django.db import models


class Position(models.TextChoices):
    GOALKEEPER = 'GK', 'Goalkeeper'
    DEFENDER = 'DEF', 'Defender'
    MIDFIELDER = 'MID', 'Midfielder'
    FORWARD = 'FWD', 'Forward'


class Team(models.Model):
    """A football club. Kept intentionally minimal for the MVP."""

    name = models.CharField(max_length=100, unique=True)
    short_name = models.CharField(max_length=20, blank=True)
    external_id = models.CharField(
        max_length=100, blank=True, null=True, unique=True,
        help_text="Stable identifier from an external data provider, if any.",
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Player(models.Model):
    """A real-world football player.

    Player identity is deliberately never derived from the display name
    alone (see AGENTS.md > Player Identity). Matching against external
    data should prefer PlayerExternalId, then PlayerAlias, and only fall
    back to fuzzy name matching as a last resort — see
    players/identity.py for the resolution service.
    """

    full_name = models.CharField(max_length=150)
    display_name = models.CharField(
        max_length=150,
        help_text="Name shown in the UI, e.g. in search results and the auction board.",
    )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=3, choices=Position.choices)
    club = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='current_players',
    )
    previous_club = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='former_players',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['display_name']),
            models.Index(fields=['full_name']),
            models.Index(fields=['position']),
        ]

    def __str__(self):
        club_name = self.club.short_name or self.club.name if self.club else 'Free agent'
        return f"{self.display_name} — {club_name} — {self.get_position_display()}"


class PlayerExternalId(models.Model):
    """Maps a Player to an identifier from an external data provider.

    This is the highest-priority identity signal: a given (provider,
    external_id) pair must resolve to exactly one player, enforced by the
    unique constraint below (see AGENTS.md invariant #7).
    """

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='external_ids')
    provider = models.CharField(max_length=50)
    external_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'external_id'],
                name='unique_provider_external_id',
            ),
        ]
        indexes = [models.Index(fields=['provider', 'external_id'])]

    def __str__(self):
        return f"{self.provider}:{self.external_id} -> {self.player}"


class AliasType(models.TextChoices):
    FULL_NAME = 'full_name', 'Full name'
    SHORT_NAME = 'short_name', 'Short name'
    NICKNAME = 'nickname', 'Nickname'
    PROVIDER_NAME = 'provider_name', 'Provider-specific name'
    ACCENTED = 'accented', 'Name with accents'
    UNACCENTED = 'unaccented', 'Name without accents'
    HISTORICAL = 'historical', 'Historical name'


class PlayerAlias(models.Model):
    """An alternate name that resolves to an existing Player.

    Aliases must always point to a real player and are never used to
    silently merge two players (see AGENTS.md > Aliases).
    """

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='aliases')
    alias = models.CharField(max_length=150)
    alias_type = models.CharField(max_length=20, choices=AliasType.choices)
    source = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['alias', 'alias_type', 'player'],
                name='unique_alias_per_player_and_type',
            ),
        ]
        indexes = [models.Index(fields=['alias'])]

    def __str__(self):
        return f"{self.alias} ({self.get_alias_type_display()}) -> {self.player}"


class MatchMethod(models.TextChoices):
    EXTERNAL_ID = 'external_id', 'Stable external ID'
    PROVIDER_ID = 'provider_id', 'Provider-specific identifier'
    CLUB_AND_NAME = 'club_and_name', 'Club + player information'
    NAME = 'name', 'Name matching'
    FUZZY = 'fuzzy', 'Fuzzy matching'
    MANUAL = 'manual', 'Manual resolution'


class PlayerIdentityMatchLog(models.Model):
    """Audit trail for every automatic (or manual) identity match attempt.

    Required by AGENTS.md: "Any automatic alias/matching mechanism must be
    auditable." Kept even for failed/ambiguous matches (player left null)
    so ambiguous cases can be reviewed later.
    """

    player = models.ForeignKey(
        Player, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='identity_match_logs',
    )
    raw_input = models.JSONField(
        help_text="Raw provider payload fragment used for matching (name, club, ids, ...).",
    )
    match_method = models.CharField(max_length=20, choices=MatchMethod.choices)
    confidence = models.FloatField(null=True, blank=True)
    matched_automatically = models.BooleanField(default=True)
    is_ambiguous = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.player_id or 'UNMATCHED'
        return f"[{self.match_method}] -> player {target} ({self.created_at:%Y-%m-%d %H:%M})"
