from decimal import Decimal

from django.test import TestCase

from auction.models import (
    Auction,
    AuctionNomination,
    AuctionTransaction,
    AvailabilityStatus,
    NominationStatus,
    PlayerAvailability,
)
from auction.services import (
    InsufficientCreditsError,
    PlayerAlreadyOwnedError,
    confirm_purchase,
    correct_transaction,
    get_manager_budget,
    roster_for,
)
from players.models import Position
from testing_utils import make_league, make_manager, make_player, make_season


def make_nomination(league, player):
    auction = Auction.objects.create(league=league, status='in_progress')
    PlayerAvailability.objects.get_or_create(
        league=league, player=player, defaults={'status': AvailabilityStatus.IN_AUCTION},
    )
    return AuctionNomination.objects.create(auction=auction, player=player)


class ConfirmPurchaseTests(TestCase):
    def setUp(self):
        self.season = make_season()
        self.league = make_league(season=self.season, initial_credits=100, allow_overspend=False)
        self.manager = make_manager(self.league, name='Alice')
        self.other_manager = make_manager(self.league, name='Bob')
        self.player = make_player('Test Striker', position=Position.FORWARD)

    def test_confirm_purchase_creates_transaction_and_marks_player_purchased(self):
        nomination = make_nomination(self.league, self.player)
        txn = confirm_purchase(nomination=nomination, manager=self.manager, price=Decimal('42'))

        self.assertEqual(txn.price, Decimal('42'))
        self.assertEqual(AuctionTransaction.objects.count(), 1)

        nomination.refresh_from_db()
        self.assertEqual(nomination.status, NominationStatus.SOLD)
        self.assertEqual(nomination.winning_manager, self.manager)

        availability = PlayerAvailability.objects.get(league=self.league, player=self.player)
        self.assertEqual(availability.status, AvailabilityStatus.PURCHASED)

    def test_a_player_cannot_be_purchased_twice_in_the_same_league(self):
        nomination = make_nomination(self.league, self.player)
        confirm_purchase(nomination=nomination, manager=self.manager, price=Decimal('10'))

        second_nomination = make_nomination(self.league, self.player)
        with self.assertRaises(PlayerAlreadyOwnedError):
            confirm_purchase(nomination=second_nomination, manager=self.other_manager, price=Decimal('5'))

    def test_manager_cannot_overspend_unless_league_allows_it(self):
        nomination = make_nomination(self.league, self.player)
        with self.assertRaises(InsufficientCreditsError):
            confirm_purchase(nomination=nomination, manager=self.manager, price=Decimal('150'))
        self.assertEqual(AuctionTransaction.objects.count(), 0)

    def test_overspend_allowed_when_league_permits_it(self):
        self.league.allow_overspend = True
        self.league.save()
        nomination = make_nomination(self.league, self.player)
        txn = confirm_purchase(nomination=nomination, manager=self.manager, price=Decimal('150'))
        self.assertEqual(txn.price, Decimal('150'))

    def test_purchased_player_no_longer_available_in_this_league_but_untouched_elsewhere(self):
        other_league = make_league(name='Other League', season=self.season, owner=self.league.owner)
        nomination = make_nomination(self.league, self.player)
        confirm_purchase(nomination=nomination, manager=self.manager, price=Decimal('10'))

        self.assertFalse(
            PlayerAvailability.objects.filter(league=other_league, player=self.player).exists()
        )


class ManagerBudgetTests(TestCase):
    def setUp(self):
        self.season = make_season()
        self.league = make_league(
            season=self.season, initial_credits=500, squad_size=3,
            slots_goalkeepers=1, slots_defenders=1, slots_midfielders=1, slots_forwards=0,
        )
        self.manager = make_manager(self.league, name='Alice')

    def test_budget_is_computed_from_the_transaction_ledger(self):
        gk = make_player('Keeper', position=Position.GOALKEEPER)
        df = make_player('Defender', position=Position.DEFENDER)

        confirm_purchase(nomination=make_nomination(self.league, gk), manager=self.manager, price=Decimal('20'))
        confirm_purchase(nomination=make_nomination(self.league, df), manager=self.manager, price=Decimal('30'))

        budget = get_manager_budget(self.manager)
        self.assertEqual(budget.total_spent, Decimal('50'))
        self.assertEqual(budget.remaining_credits, Decimal('450'))
        self.assertEqual(budget.players_purchased, 2)
        self.assertEqual(budget.remaining_slots, 1)
        self.assertEqual(budget.position_slots_remaining[Position.GOALKEEPER], 0)
        self.assertEqual(budget.position_slots_remaining[Position.DEFENDER], 0)
        self.assertEqual(budget.average_purchase_price, Decimal('25'))

    def test_correction_updates_effective_price_without_deleting_original(self):
        player = make_player('Winger', position=Position.MIDFIELDER)
        original = confirm_purchase(
            nomination=make_nomination(self.league, player), manager=self.manager, price=Decimal('40'),
        )
        correct_transaction(original=original, new_price=Decimal('35'))

        original.refresh_from_db()
        self.assertEqual(original.price, Decimal('40'))
        self.assertEqual(AuctionTransaction.objects.filter(player=player).count(), 2)

        budget = get_manager_budget(self.manager)
        self.assertEqual(budget.total_spent, Decimal('35'))

        roster = roster_for(self.manager)
        self.assertEqual(len(roster), 1)
        self.assertEqual(roster[0].price, Decimal('35'))

    def test_roster_only_includes_this_managers_players(self):
        other_manager = make_manager(self.league, name='Bob')
        mine = make_player('Mine', position=Position.GOALKEEPER)
        theirs = make_player('Theirs', position=Position.DEFENDER)

        confirm_purchase(nomination=make_nomination(self.league, mine), manager=self.manager, price=Decimal('10'))
        confirm_purchase(nomination=make_nomination(self.league, theirs), manager=other_manager, price=Decimal('10'))

        roster = roster_for(self.manager)
        self.assertEqual([txn.player for txn in roster], [mine])
