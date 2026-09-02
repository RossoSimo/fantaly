"""Auction domain logic.

Business rules that affect credits or player ownership live here so they
are reusable from views, a future API, management commands, and tests
(see AGENTS.md > API Design and > Domain Logic), and so every entry point
gets the same invariant checks rather than re-implementing them.
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from players.models import Position

from .models import (
    AuctionTransaction,
    AvailabilityStatus,
    NominationStatus,
    PlayerAvailability,
)

logger = logging.getLogger('auction')


class InsufficientCreditsError(ValidationError):
    pass


class PlayerAlreadyOwnedError(ValidationError):
    pass


@transaction.atomic
def confirm_purchase(*, nomination, manager, price: Decimal, user=None, notes: str = '') -> AuctionTransaction:
    """Record a completed purchase: creates the ledger entry, updates the
    nomination, marks the player unavailable, and lets the manager's
    budget/roster reflect the change (which are always derived from this
    ledger, never stored redundantly).

    Raises PlayerAlreadyOwnedError or InsufficientCreditsError if the
    purchase would violate a data-integrity invariant; the caller (a view,
    typically) is expected to surface that back to the user — the auction
    is advisory and never auto-corrects itself.
    """
    league = nomination.auction.league
    player = nomination.player

    if manager.league_id != league.id:
        raise ValidationError("Manager does not belong to this league.")

    if AuctionTransaction.objects.filter(league=league, player=player, is_correction=False).exists():
        raise PlayerAlreadyOwnedError(
            f"{player} has already been purchased in this league."
        )

    if not league.allow_overspend:
        budget = get_manager_budget(manager)
        if price > budget.remaining_credits:
            raise InsufficientCreditsError(
                f"{manager} has {budget.remaining_credits} credits remaining, "
                f"cannot spend {price}."
            )

    txn = AuctionTransaction.objects.create(
        auction=nomination.auction,
        league=league,
        season=league.season,
        player=player,
        manager=manager,
        nomination=nomination,
        price=price,
        notes=notes,
        created_by=user,
    )

    nomination.status = NominationStatus.SOLD
    nomination.winning_manager = manager
    nomination.current_bid = price
    nomination.save(update_fields=['status', 'winning_manager', 'current_bid'])

    PlayerAvailability.objects.update_or_create(
        league=league, player=player,
        defaults={'status': AvailabilityStatus.PURCHASED},
    )

    logger.info(
        "auction.purchase_confirmed league=%s player=%s manager=%s price=%s",
        league.pk, player.pk, manager.pk, price,
    )
    return txn


@transaction.atomic
def correct_transaction(*, original: AuctionTransaction, new_price: Decimal, user=None, notes: str = '') -> AuctionTransaction:
    """Create an adjustment transaction for a previously recorded purchase
    rather than mutating history in place (see AGENTS.md invariant #4)."""
    if original.is_correction:
        raise ValidationError("Cannot correct a correction; correct the original transaction instead.")

    correction = AuctionTransaction.objects.create(
        auction=original.auction,
        league=original.league,
        season=original.season,
        player=original.player,
        manager=original.manager,
        nomination=original.nomination,
        price=new_price,
        notes=notes,
        is_correction=True,
        corrects=original,
        created_by=user,
    )
    logger.info(
        "auction.transaction_corrected league=%s player=%s original_txn=%s new_price=%s",
        original.league_id, original.player_id, original.pk, new_price,
    )
    return correction


def effective_transactions(league) -> list[AuctionTransaction]:
    """Return the currently-effective transaction per player for a league:
    the most recent correction if one exists, otherwise the original
    purchase. This is what "current roster" and "credits spent" are
    computed from.
    """
    all_txns = (
        AuctionTransaction.objects.filter(league=league)
        .select_related('player', 'manager')
        .order_by('player_id', '-purchased_at')
    )
    latest_by_player = {}
    for txn in all_txns:
        latest_by_player.setdefault(txn.player_id, txn)
    return list(latest_by_player.values())


def roster_for(manager) -> list[AuctionTransaction]:
    """The manager's current roster, derived from the transaction ledger."""
    return [
        txn for txn in effective_transactions(manager.league)
        if txn.manager_id == manager.id
    ]


@dataclass
class ManagerBudget:
    initial_credits: int
    total_spent: Decimal
    remaining_credits: Decimal
    players_purchased: int
    remaining_slots: int
    position_slots_remaining: dict = field(default_factory=dict)
    average_purchase_price: Decimal | None = None


def get_manager_budget(manager) -> ManagerBudget:
    """Compute a manager's budget from the transaction ledger — credits are
    never manually maintained (see AGENTS.md > Manager Budgets)."""
    league = manager.league
    roster = roster_for(manager)

    total_spent = sum((txn.price for txn in roster), Decimal('0'))
    players_purchased = len(roster)
    remaining_slots = max(league.squad_size - players_purchased, 0)

    slot_totals = {
        Position.GOALKEEPER: league.slots_goalkeepers,
        Position.DEFENDER: league.slots_defenders,
        Position.MIDFIELDER: league.slots_midfielders,
        Position.FORWARD: league.slots_forwards,
    }
    purchased_by_position = {pos: 0 for pos in slot_totals}
    for txn in roster:
        purchased_by_position[txn.player.position] = purchased_by_position.get(txn.player.position, 0) + 1
    position_slots_remaining = {
        pos: max(slot_totals[pos] - purchased_by_position.get(pos, 0), 0) for pos in slot_totals
    }

    average_price = (total_spent / players_purchased) if players_purchased else None

    return ManagerBudget(
        initial_credits=league.initial_credits,
        total_spent=total_spent,
        remaining_credits=Decimal(league.initial_credits) - total_spent,
        players_purchased=players_purchased,
        remaining_slots=remaining_slots,
        position_slots_remaining=position_slots_remaining,
        average_purchase_price=average_price,
    )
