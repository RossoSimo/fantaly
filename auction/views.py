from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from leagues.models import FantasyManager, League
from players.models import Player

from .models import (
    Auction,
    AuctionNomination,
    AuctionTransaction,
    AvailabilityStatus,
    NominationStatus,
    PlayerAvailability,
)
from .services import confirm_purchase, get_manager_budget


class LeagueMemberMixin(LoginRequiredMixin):
    def get_league(self):
        return get_object_or_404(
            League.objects.filter(memberships__user=self.request.user),
            pk=self.kwargs['league_pk'],
        )


class AuctionDashboardView(LeagueMemberMixin, View):
    """The live auction board (see AGENTS.md > Auction Dashboard):
    current player, budgets, availability, and recent purchases, all in
    one screen that works well on mobile."""

    def get(self, request, league_pk):
        league = self.get_league()
        auction = Auction.objects.filter(league=league).exclude(
            status='completed'
        ).order_by('-created_at').first()

        open_nomination = None
        if auction:
            open_nomination = auction.nominations.filter(
                status=NominationStatus.IN_PROGRESS
            ).select_related('player').first()

        managers = list(league.managers.all())
        budgets = {manager.id: get_manager_budget(manager) for manager in managers}

        recent_purchases = (
            AuctionTransaction.objects.filter(league=league, is_correction=False)
            .select_related('player', 'manager')
            .order_by('-purchased_at')[:10]
        )

        available_players = Player.objects.filter(
            availabilities__league=league, availabilities__status=AvailabilityStatus.AVAILABLE,
        ).order_by('display_name')[:50]

        return render(request, 'auction/dashboard.html', {
            'league': league,
            'auction': auction,
            'open_nomination': open_nomination,
            'managers': managers,
            'budgets': budgets,
            'recent_purchases': recent_purchases,
            'available_players': available_players,
        })


class NominatePlayerView(LeagueMemberMixin, View):
    def post(self, request, league_pk):
        league = self.get_league()
        auction, _ = Auction.objects.get_or_create(
            league=league, status='in_progress', defaults={'name': 'Live auction'},
        )
        player = get_object_or_404(Player, pk=request.POST.get('player_id'))

        availability, _ = PlayerAvailability.objects.get_or_create(
            league=league, player=player, defaults={'status': AvailabilityStatus.AVAILABLE},
        )
        if availability.status != AvailabilityStatus.AVAILABLE:
            messages.error(request, f"{player} is not available to nominate.")
            return redirect('auction:dashboard', league_pk=league.pk)

        AuctionNomination.objects.create(auction=auction, player=player)
        availability.status = AvailabilityStatus.IN_AUCTION
        availability.save(update_fields=['status'])

        return redirect('auction:dashboard', league_pk=league.pk)


class ConfirmPurchaseView(LeagueMemberMixin, View):
    def post(self, request, league_pk, nomination_pk):
        league = self.get_league()
        nomination = get_object_or_404(
            AuctionNomination, pk=nomination_pk, auction__league=league,
        )
        manager = get_object_or_404(FantasyManager, pk=request.POST.get('manager_id'), league=league)

        try:
            price = Decimal(request.POST.get('price', ''))
        except InvalidOperation:
            messages.error(request, "Enter a valid price.")
            return redirect('auction:dashboard', league_pk=league.pk)

        try:
            confirm_purchase(nomination=nomination, manager=manager, price=price, user=request.user)
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc))
            return redirect('auction:dashboard', league_pk=league.pk)

        messages.success(request, f"{nomination.player} assigned to {manager} for {price}.")
        return redirect('auction:dashboard', league_pk=league.pk)
