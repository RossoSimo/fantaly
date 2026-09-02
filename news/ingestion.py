"""News ingestion service.

Providers should call `ingest_news_item()` for each item they retrieve
rather than creating PlayerNews rows directly, so deduplication logic
lives in one place (see AGENTS.md > News and RSS).
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from django.db import IntegrityError

from players.models import Player, Team

from .models import NewsCategory, NewsSource, PlayerNews

logger = logging.getLogger('providers')


@dataclass
class InboundNewsItem:
    source: NewsSource
    title: str
    url: str
    summary: str = ''
    external_id: str | None = None
    published_at: datetime | None = None
    category: str = NewsCategory.GENERAL
    player: Player | None = None
    club: Team | None = None


def ingest_news_item(item: InboundNewsItem) -> tuple[PlayerNews, bool]:
    """Create a PlayerNews row if it hasn't been seen before.

    Returns (news_item, created). Prefers the source's stable external_id
    for dedup; falls back to an exact (source, title, published_at) match
    when no external_id is available.
    """
    if item.external_id:
        existing = PlayerNews.objects.filter(
            source=item.source, external_id=item.external_id,
        ).first()
        if existing:
            return existing, False
    else:
        existing = PlayerNews.objects.filter(
            source=item.source, title=item.title, published_at=item.published_at,
        ).first()
        if existing:
            return existing, False

    try:
        news = PlayerNews.objects.create(
            player=item.player,
            club=item.club,
            source=item.source,
            title=item.title,
            summary=item.summary,
            url=item.url,
            external_id=item.external_id,
            category=item.category,
            published_at=item.published_at,
        )
        return news, True
    except IntegrityError:
        # Race with another ingestion run hitting the same unique
        # constraint; treat as already-imported rather than failing loudly.
        logger.info(
            "news.ingest.race_detected source=%s external_id=%s",
            item.source.pk if item.source else None, item.external_id,
        )
        existing = PlayerNews.objects.get(source=item.source, external_id=item.external_id)
        return existing, False
