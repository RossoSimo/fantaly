"""Player identity resolution.

Implements the matching priority described in AGENTS.md > Player Identity:

    1. Stable external player ID.
    2. Provider-specific identifier.
    3. Club + player information.
    4. Name matching.
    5. Fuzzy matching only as a last resort.

Every attempt — matched, ambiguous, or unmatched — is recorded via
PlayerIdentityMatchLog so automatic matching stays auditable. This module
intentionally never merges two Player rows automatically; ambiguous results
come back as unmatched with is_ambiguous=True for manual review.
"""

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .models import MatchMethod, Player, PlayerAlias, PlayerExternalId

# Below this similarity ratio, a fuzzy match is not considered viable at all.
FUZZY_MATCH_MIN_RATIO = 0.85


@dataclass
class ExternalPlayerRecord:
    """Normalized shape of an inbound provider payload used for matching.

    Providers should map their raw payloads to this before calling
    resolve_player(), keeping provider-specific parsing out of the
    matching logic itself (see AGENTS.md > Data Sources).
    """

    provider: str
    external_id: str | None = None
    full_name: str = ''
    club_name: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class MatchResult:
    player: Player | None
    method: str
    confidence: float | None
    is_ambiguous: bool = False


def resolve_player(record: ExternalPlayerRecord) -> MatchResult:
    """Resolve an external record to a Player, logging the attempt.

    Returns a MatchResult with player=None when no confident match is
    found. Callers are responsible for deciding what to do with an
    unmatched or ambiguous result (e.g. surface it for manual review) —
    this function never creates or merges Player records.
    """
    result = (
            _match_by_external_id(record)
            or _match_by_club_and_name(record)
            or _match_by_name(record)
            or _match_by_fuzzy_name(record)
    )
    if result is None:
        result = MatchResult(player=None, method=MatchMethod.FUZZY, confidence=None)

    PlayerIdentityMatchLogWriter.write(record, result)
    return result


def _match_by_external_id(record: ExternalPlayerRecord) -> MatchResult | None:
    if not record.external_id:
        return None
    mapping = (
        PlayerExternalId.objects.select_related('player')
        .filter(provider=record.provider, external_id=record.external_id)
        .first()
    )
    if mapping is None:
        return None
    return MatchResult(player=mapping.player, method=MatchMethod.EXTERNAL_ID, confidence=1.0)


def _match_by_club_and_name(record: ExternalPlayerRecord) -> MatchResult | None:
    if not record.club_name or not record.full_name:
        return None
    candidates = list(
        Player.objects.filter(
            club__name__iexact=record.club_name,
        ).filter(
            models_q_name_matches(record.full_name)
        )
    )
    return _single_confident_match(candidates, MatchMethod.CLUB_AND_NAME, confidence=0.9)


def _match_by_name(record: ExternalPlayerRecord) -> MatchResult | None:
    if not record.full_name:
        return None
    candidates = list(Player.objects.filter(models_q_name_matches(record.full_name)))
    return _single_confident_match(candidates, MatchMethod.NAME, confidence=0.7)


def _match_by_fuzzy_name(record: ExternalPlayerRecord) -> MatchResult | None:
    """Last-resort fuzzy match. When a club is known, the candidate pool
    is restricted to players at that club — a shared surname across
    *different* clubs (e.g. two unrelated players both called "Martinez")
    is exactly the kind of collision fuzzy matching must not paper over.
    Without a club hint, it falls back to the full player pool, since
    that's genuinely the only signal available.
    """
    if not record.full_name:
        return None
    candidate_qs = Player.objects.only('id', 'full_name', 'display_name', 'club')
    if record.club_name:
        candidate_qs = candidate_qs.filter(club__name__iexact=record.club_name)

    best_player = None
    best_ratio = 0.0
    tied = False
    target = record.full_name.strip().lower()
    for player in candidate_qs:
        for candidate_name in (player.full_name, player.display_name):
            ratio = SequenceMatcher(None, target, candidate_name.strip().lower()).ratio()
            if ratio > best_ratio:
                best_ratio, best_player, tied = ratio, player, False
            elif ratio == best_ratio and best_player is not None and ratio > 0:
                tied = True
    if best_player is None or best_ratio < FUZZY_MATCH_MIN_RATIO:
        return MatchResult(player=None, method=MatchMethod.FUZZY, confidence=best_ratio or None)
    if tied:
        return MatchResult(
            player=None, method=MatchMethod.FUZZY, confidence=best_ratio, is_ambiguous=True,
        )
    return MatchResult(player=best_player, method=MatchMethod.FUZZY, confidence=best_ratio)


def _single_confident_match(candidates, method: str, confidence: float) -> MatchResult | None:
    if not candidates:
        return None
    if len(candidates) > 1:
        return MatchResult(player=None, method=method, confidence=None, is_ambiguous=True)
    return MatchResult(player=candidates[0], method=method, confidence=confidence)


def models_q_name_matches(full_name: str):
    """Build a Q object matching a player's canonical name or any alias.

    Kept as a small helper so both name-based matchers share one
    definition of "does this name match this player".
    """
    from django.db.models import Q

    alias_player_ids = PlayerAlias.objects.filter(
        alias__iexact=full_name
    ).values_list('player_id', flat=True)
    return Q(full_name__iexact=full_name) | Q(display_name__iexact=full_name) | Q(
        id__in=list(alias_player_ids)
    )


class PlayerIdentityMatchLogWriter:
    """Isolated so tests can monkeypatch/inspect logging without touching
    the matching algorithm itself."""

    @staticmethod
    def write(record: ExternalPlayerRecord, result: MatchResult):
        from .models import PlayerIdentityMatchLog

        PlayerIdentityMatchLog.objects.create(
            player=result.player,
            raw_input={
                'provider': record.provider,
                'external_id': record.external_id,
                'full_name': record.full_name,
                'club_name': record.club_name,
                **record.raw,
            },
            match_method=result.method,
            confidence=result.confidence,
            matched_automatically=True,
            is_ambiguous=result.is_ambiguous,
        )
