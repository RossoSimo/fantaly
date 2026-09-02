from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from .models import FantasyManager, League, LeagueMembership, LeagueRole


class UserLeaguesMixin(LoginRequiredMixin):
    """Restricts querysets to leagues the requesting user is a member of
    (owner, manager, or viewer) — see AGENTS.md > Authentication and
    Authorization: league membership must be explicit."""

    def get_queryset(self):
        return League.objects.filter(memberships__user=self.request.user).distinct()


class LeagueListView(UserLeaguesMixin, ListView):
    model = League
    template_name = 'leagues/league_list.html'
    context_object_name = 'leagues'


class LeagueDetailView(UserLeaguesMixin, DetailView):
    model = League
    template_name = 'leagues/league_detail.html'
    context_object_name = 'league'


class LeagueCreateView(LoginRequiredMixin, CreateView):
    model = League
    fields = [
        'name', 'season', 'num_managers', 'initial_credits', 'squad_size',
        'slots_goalkeepers', 'slots_defenders', 'slots_midfielders', 'slots_forwards',
        'min_bid', 'max_bid', 'allow_overspend',
    ]
    template_name = 'leagues/league_form.html'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        LeagueMembership.objects.create(
            league=self.object, user=self.request.user, role=LeagueRole.OWNER,
        )
        return response

    def get_success_url(self):
        return reverse_lazy('leagues:detail', kwargs={'pk': self.object.pk})

class AddManagerView(LoginRequiredMixin, View):
    """Adds a FantasyManager to a league. Deliberately not tied to a User
    account — see AGENTS.md > Authentication and Authorization and the
    FantasyManager docstring: most participants never log in themselves."""

    def post(self, request, pk):
        league = get_object_or_404(
            League.objects.filter(memberships__user=request.user), pk=pk,
        )
        name = request.POST.get('name', '').strip()
        if name:
            FantasyManager.objects.get_or_create(league=league, name=name)
        return redirect('leagues:detail', pk=league.pk)