import hashlib
from unittest.mock import MagicMock, patch

import pytest

from src.fetcher import NewsItem, HNFetcher, RSSFetcher


class TestNewsItemHash:
    def test_hash_is_md5_of_url(self):
        item = NewsItem(title="T", url="https://example.com/a", source="S")
        expected = hashlib.md5("https://example.com/a".encode()).hexdigest()
        assert item.hash == expected

    def test_hash_is_deterministic(self):
        url = "https://example.com/stable"
        assert NewsItem(title="A", url=url, source="S").hash == NewsItem(title="B", url=url, source="S").hash

    def test_different_urls_produce_different_hashes(self):
        a = NewsItem(title="T", url="https://example.com/a", source="S")
        b = NewsItem(title="T", url="https://example.com/b", source="S")
        assert a.hash != b.hash

    def test_hash_length_is_32(self):
        item = NewsItem(title="T", url="https://x.com", source="S")
        assert len(item.hash) == 32


class TestHNFetcher:
    def _mock_response(self, hits):
        resp = MagicMock()
        resp.json.return_value = {"hits": hits}
        resp.raise_for_status.return_value = None
        return resp

    def test_returns_news_items_from_hits(self):
        hits = [
            {"title": "LLM paper", "url": "https://arxiv.org/1", "objectID": "1", "created_at": "2024-01-01"},
        ]
        with patch("src.fetcher.httpx.get", return_value=self._mock_response(hits)):
            items = HNFetcher().fetch()
        assert len(items) == 1
        assert items[0].title == "LLM paper"
        assert items[0].source == "Hacker News"

    def test_uses_hn_fallback_url_when_url_missing(self):
        hits = [{"title": "Ask HN", "url": None, "objectID": "42", "created_at": ""}]
        with patch("src.fetcher.httpx.get", return_value=self._mock_response(hits)):
            items = HNFetcher().fetch()
        assert "news.ycombinator.com/item?id=42" in items[0].url

    def test_returns_empty_list_on_http_error(self):
        with patch("src.fetcher.httpx.get", side_effect=Exception("timeout")):
            items = HNFetcher().fetch()
        assert items == []

    def test_returns_empty_list_when_hits_missing(self):
        resp = MagicMock()
        resp.json.return_value = {}
        resp.raise_for_status.return_value = None
        with patch("src.fetcher.httpx.get", return_value=resp):
            items = HNFetcher().fetch()
        assert items == []


class TestRSSFetcher:
    def _mock_feed(self, entries):
        feed = MagicMock()
        feed.entries = []
        for e in entries:
            entry = MagicMock()
            entry.get = lambda k, default="", _e=e: _e.get(k, default)
            feed.entries.append(entry)
        return feed

    def test_returns_items_from_feed(self):
        entries = [{"title": "New model", "link": "https://hf.co/post", "summary": "...", "published": ""}]
        with patch("src.fetcher.feedparser.parse", return_value=self._mock_feed(entries)):
            items = RSSFetcher("https://hf.co/feed.xml", "HuggingFace").fetch()
        assert len(items) == 1
        assert items[0].title == "New model"
        assert items[0].source == "HuggingFace"

    def test_returns_empty_list_on_parse_error(self):
        with patch("src.fetcher.feedparser.parse", side_effect=Exception("parse error")):
            items = RSSFetcher("https://bad-feed.com/rss", "Bad Feed").fetch()
        assert items == []
