from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, F, FilteredRelation, IntegerField, OuterRef, Q, Subquery, When
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from market.aggregation import get_market_summary
from market.models import MarketPriceObservation, PriceType
from players.models import Player, Position, Team
from seasons.models import Season
from stats.models import PlayerStatus
from stats.services import current_season, default_stats_season

SORTABLE = {
    'name': 'display_name',
    'club': 'club__name',
    'position': 'position_rank',
    'appearances': 'stats_appearances',
    'goals': 'stats_goals',
    'assists': 'stats_assists',
    'average_rating': 'stats_average_rating',
    'fantasy_average': 'stats_fantasy_average',
    'quotation': 'quotation',
}

STAT_SORTS = {
    'appearances', 'goals', 'assists', 'average_rating', 'fantasy_average', 'quotation',
}

POSITION_RANK = Case(
    When(position=Position.GOALKEEPER, then=0),
    When(position=Position.DEFENDER, then=1),
    When(position=Position.MIDFIELDER, then=2),
    When(position=Position.FORWARD, then=3),
    default=9,
    output_field=IntegerField(),
)


class PlayerListView(LoginRequiredMixin, ListView):
    """Fast player search — always shows position + club alongside the
    name so two similarly-named players are never ambiguous in the
    results (see AGENTS.md > Search). Season stats are shown for a chosen
    season (previous season by default, which is what auction prep needs).
    """

    model = Player
    template_name = 'players/player_list.html'
    context_object_name = 'players'
    paginate_by = 50

    def get_queryset(self):
        stats_season = self._stats_season()
        quote_season = current_season() or stats_season

        qs = Player.objects.select_related('club').annotate(position_rank=POSITION_RANK)

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

        club_id = self.request.GET.get('club', '').strip()
        if club_id.isdigit():
            qs = qs.filter(club_id=int(club_id))

        active = self.request.GET.get('active', '1')
        if active == '1':
            qs = qs.filter(is_active=True)
        elif active == '0':
            qs = qs.filter(is_active=False)

        if stats_season is not None:
            qs = qs.annotate(
                listed_stats=FilteredRelation(
                    'season_stats',
                    condition=Q(season_stats__season=stats_season),
                ),
                stats_appearances=F('listed_stats__appearances'),
                stats_goals=F('listed_stats__goals'),
                stats_assists=F('listed_stats__assists'),
                stats_average_rating=F('listed_stats__average_rating'),
                stats_fantasy_average=F('listed_stats__fantasy_average'),
            )

        if quote_season is not None:
            latest_quote = (
                MarketPriceObservation.objects.filter(
                    player=OuterRef('pk'),
                    season=quote_season,
                    price_type=PriceType.ESTIMATED,
                )
                .order_by('-observed_at')
                .values('price')[:1]
            )
            qs = qs.annotate(quotation=Subquery(latest_quote))

        return self._apply_sort(qs)

    def _apply_sort(self, qs):
        sort_key = self.request.GET.get('sort', 'name')
        if sort_key not in SORTABLE:
            sort_key = 'name'
        field = SORTABLE[sort_key]
        descending = self.request.GET.get('dir', 'desc' if sort_key in STAT_SORTS else 'asc') == 'desc'
        if field not in qs.query.annotations and field not in (
            'display_name', 'club__name', 'position_rank',
        ):
            return qs.order_by('display_name')
        expression = F(field)
        ordered = expression.desc(nulls_last=True) if descending else expression.asc(nulls_last=True)
        return qs.order_by(ordered, 'display_name')

    def _stats_season(self):
        label = self.request.GET.get('season', '').strip()
        if label:
            return Season.objects.filter(label=label).first()
        return default_stats_season()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        base_params = params.copy()
        base_params.pop('sort', None)
        base_params.pop('dir', None)
        sort_key = self.request.GET.get('sort', 'name')
        default_dir = 'desc' if sort_key in STAT_SORTS else 'asc'
        context.update({
            'query': self.request.GET.get('q', ''),
            'position': self.request.GET.get('position', ''),
            'club_id': self.request.GET.get('club', ''),
            'active': self.request.GET.get('active', '1'),
            'sort': sort_key if sort_key in SORTABLE else 'name',
            'dir': self.request.GET.get('dir', default_dir),
            'teams': Team.objects.filter(current_players__isnull=False).distinct().order_by('name'),
            'seasons': Season.objects.all(),
            'stats_season': self._stats_season(),
            'filter_query': params.urlencode(),
            'sort_query': base_params.urlencode(),
        })
        return context


class PlayerDetailView(LoginRequiredMixin, DetailView):
    model = Player
    template_name = 'players/player_detail.html'
    context_object_name = 'player'

    def get_queryset(self):
        return Player.objects.select_related('club', 'previous_club').prefetch_related(
            'aliases',
            'season_stats__season',
            'season_stats__club',
            'statuses__season',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        player = self.object
        season_stats = list(player.season_stats.all())
        season_stats.sort(key=lambda row: row.season.year_start, reverse=True)
        context['season_stats'] = season_stats

        season = current_season() or default_stats_season()
        context['current_status'] = (
            PlayerStatus.current_for(player, season) if season else None
        )
        context['market_summary'] = (
            get_market_summary(player, season) if season else None
        )
        context['estimated_quotation'] = None
        if season:
            context['estimated_quotation'] = (
                MarketPriceObservation.objects.filter(
                    player=player, season=season, price_type=PriceType.ESTIMATED,
                )
                .order_by('-observed_at')
                .first()
            )
        return context


class PlayerCreateView(LoginRequiredMixin, CreateView):
    """Manual player entry for a player the listone importer missed."""

    model = Player
    fields = [
        'full_name', 'display_name', 'first_name', 'last_name',
        'date_of_birth', 'nationality', 'position', 'club', 'previous_club', 'is_active',
    ]
    template_name = 'players/player_form.html'

    def get_success_url(self):
        return reverse_lazy('players:detail', kwargs={'pk': self.object.pk})
