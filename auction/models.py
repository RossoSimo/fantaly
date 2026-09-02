from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from leagues.models import FantasyManager, League
from players.models import Player
from seasons.models import Season


class AvailabilityStatus(models.TextChoices):
    AVAILABLE = 'available', 'Available'
    IN_AUCTION = 'in_auction', 'Currently being auctioned'
    PURCHASED = 'purchased', 'Purchased'
    UNSOLD = 'unsold', 'Unsold'
    UNAVAILABLE = 'unavailable', 'Unavailable'
    WITHDRAWN = 'withdrawn', 'Withdrawn'


class PlayerAvailability(models.Model):
    """The single source of truth for whether a player can be nominated in
    a given league right now (see AGENTS.md > Player Availability).

    A player purchased in one league no longer appears as available there,
    but stays untouched in every other league (invariant #3 / #8).
    """

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='player_availabilities')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='availabilities')
    status = models.CharField(max_length=15, choices=AvailabilityStatus.choices, default=AvailabilityStatus.AVAILABLE)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'player availabilities'
        constraints = [
            models.UniqueConstraint(fields=['league', 'player'], name='unique_availability_per_league_player'),
        ]
        indexes = [models.Index(fields=['league', 'status'])]

    def __str__(self):
        return f"{self.player} @ {self.league}: {self.get_status_display()}"


class AuctionStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    IN_PROGRESS = 'in_progress', 'In progress'
    COMPLETED = 'completed', 'Completed'


class Auction(models.Model):
    """One auction session for a league.

    The app records what a user reports happened in a real-world auction;
    it does not conduct or enforce the auction itself (see AGENTS.md >
    Auction System).
    """

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='auctions')
    name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=15, choices=AuctionStatus.choices, default=AuctionStatus.DRAFT)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name or f"Auction #{self.pk} — {self.league}"

    @property
    def season(self) -> Season:
        return self.league.season


class NominationStatus(models.TextChoices):
    IN_PROGRESS = 'in_progress', 'In progress'
    SOLD = 'sold', 'Sold'
    UNSOLD = 'unsold', 'Unsold'
    WITHDRAWN = 'withdrawn', 'Withdrawn'


class AuctionNomination(models.Model):
    """One instance of a player being put up for bidding within an
    auction. A player may be nominated more than once across an auction
    (e.g. unsold, then brought back later)."""

    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='nominations')
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='nominations')
    status = models.CharField(max_length=15, choices=NominationStatus.choices, default=NominationStatus.IN_PROGRESS)
    current_bid = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    winning_manager = models.ForeignKey(
        FantasyManager, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_nominations',
    )
    nominated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-nominated_at']
        indexes = [models.Index(fields=['auction', 'status'])]

    def __str__(self):
        return f"{self.player} in {self.auction} ({self.get_status_display()})"


class Bid(models.Model):
    """A single bid placed during a nomination. Optional granular detail
    on top of the winning price recorded in the final AuctionTransaction —
    useful for a full audit trail of how the price was reached."""

    nomination = models.ForeignKey(AuctionNomination, on_delete=models.CASCADE, related_name='bids')
    manager = models.ForeignKey(FantasyManager, on_delete=models.CASCADE, related_name='bids')
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    placed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['placed_at']

    def __str__(self):
        return f"{self.manager} bid {self.amount} on {self.nomination}"


class AuctionTransaction(models.Model):
    """The immutable ledger of completed purchases.

    This is the source of truth for spent credits and roster membership.
    Historical rows are never edited in place — a correction creates a new
    row pointing back at the one it corrects via `corrects`
    (see AGENTS.md > Manager Budgets and invariant #4).
    """

    auction = models.ForeignKey(Auction, on_delete=models.PROTECT, related_name='transactions')
    league = models.ForeignKey(League, on_delete=models.PROTECT, related_name='transactions')
    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name='transactions')
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='auction_transactions')
    manager = models.ForeignKey(FantasyManager, on_delete=models.PROTECT, related_name='transactions')
    nomination = models.ForeignKey(
        AuctionNomination, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions',
    )

    price = models.DecimalField(max_digits=6, decimal_places=2)
    purchased_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    is_correction = models.BooleanField(default=False)
    corrects = models.ForeignKey(
        'self', on_delete=models.PROTECT, null=True, blank=True, related_name='corrections',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ['-purchased_at']
        constraints = [
            # A player can only be actively owned by one manager per league
            # (invariant #1). Corrections are excluded — they reference the
            # same player again on purpose.
            models.UniqueConstraint(
                fields=['league', 'player'],
                condition=models.Q(is_correction=False),
                name='unique_original_purchase_per_league_player',
            ),
        ]
        indexes = [
            models.Index(fields=['league', 'manager']),
            models.Index(fields=['league', 'player']),
        ]

    def __str__(self):
        kind = 'correction' if self.is_correction else 'purchase'
        return f"{self.player} -> {self.manager} for {self.price} ({kind})"

    def clean(self):
        if self.league_id and self.auction_id and self.auction.league_id != self.league_id:
            raise ValidationError("Transaction league must match its auction's league.")
        if self.is_correction and not self.corrects_id:
            raise ValidationError({'corrects': "A correction must reference the transaction it corrects."})
