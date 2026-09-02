from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from .models import Player


class PlayerListView(LoginRequiredMixin, ListView):
    """Fast player search — always shows position + club alongside the
    name so two similarly-named players are never ambiguous in the
    results (see AGENTS.md > Search)."""

    model = Player
    template_name = 'players/player_list.html'
    context_object_name = 'players'
    paginate_by = 30

    def get_queryset(self):
        qs = Player.objects.select_related('club').order_by('display_name')
        query = self.request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(
                Q(display_name__icontains=query)
                | Q(full_name__icontains=query)
                | Q(aliases__alias__icontains=query)
                | Q(club__name__icontains=query)
            ).distinct()
        position = self.request.GET.get('position', '').strip()
        if position:
            qs = qs.filter(position=position)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['position'] = self.request.GET.get('position', '')
        return context


class PlayerDetailView(LoginRequiredMixin, DetailView):
    model = Player
    template_name = 'players/player_detail.html'
    context_object_name = 'player'

    def get_queryset(self):
        return Player.objects.select_related('club', 'previous_club').prefetch_related(
            'aliases', 'season_stats__season', 'statuses__season',
        )


class PlayerCreateView(LoginRequiredMixin, CreateView):
    """Manual player entry. Bulk import via external providers is a
    separate, not-yet-built pipeline (see AGENTS.md > Data Sources) — this
    covers the case of a manager adding a player the importer missed."""

    model = Player
    fields = [
        'full_name', 'display_name', 'first_name', 'last_name',
        'date_of_birth', 'nationality', 'position', 'club', 'previous_club', 'is_active',
    ]
    template_name = 'players/player_form.html'

    def get_success_url(self):
        return reverse_lazy('players:detail', kwargs={'pk': self.object.pk})