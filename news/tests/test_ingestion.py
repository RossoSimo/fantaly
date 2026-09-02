from django.test import TestCase
from django.utils import timezone

from news.ingestion import InboundNewsItem, ingest_news_item
from news.models import NewsCategory, NewsSource, PlayerNews
from testing_utils import make_player


class NewsIngestionDedupTests(TestCase):
    def setUp(self):
        self.source = NewsSource.objects.create(name='Test RSS', feed_url='https://example.com/feed')
        self.player = make_player('News Subject')

    def test_same_external_id_is_not_imported_twice(self):
        item = InboundNewsItem(
            source=self.source, title='Injury update', url='https://example.com/1',
            external_id='abc-123', player=self.player, category=NewsCategory.INJURY,
            published_at=timezone.now(),
        )
        _, created_first = ingest_news_item(item)
        _, created_second = ingest_news_item(item)

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(PlayerNews.objects.count(), 1)

    def test_items_without_external_id_dedup_on_source_title_and_date(self):
        published = timezone.now()
        item = InboundNewsItem(
            source=self.source, title='Training resumed', url='https://example.com/2',
            player=self.player, published_at=published,
        )
        ingest_news_item(item)
        _, created_again = ingest_news_item(item)

        self.assertFalse(created_again)
        self.assertEqual(PlayerNews.objects.count(), 1)

    def test_distinct_items_are_both_stored(self):
        item1 = InboundNewsItem(source=self.source, title='A', url='https://example.com/a', external_id='1')
        item2 = InboundNewsItem(source=self.source, title='B', url='https://example.com/b', external_id='2')
        ingest_news_item(item1)
        ingest_news_item(item2)
        self.assertEqual(PlayerNews.objects.count(), 2)
