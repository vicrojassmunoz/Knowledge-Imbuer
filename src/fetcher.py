import hashlib
import httpx
import feedparser
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel, computed_field

from src.config import HN_QUERY, HN_MIN_POINTS, HN_URL, RSS_SOURCES

logger = logging.getLogger(__name__)


class NewsItem(BaseModel):
    title: str
    url: str
    source: str
    summary: str = ""
    published: str = ""
    one_liner: str = ""
    score: int = 0

    @computed_field
    @property
    def hash(self) -> str:
        return hashlib.md5(self.url.encode()).hexdigest()


class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self) -> list[NewsItem]:
        ...


class RSSFetcher(BaseFetcher):
    def __init__(self, url: str, source_name: str):
        self.url = url
        self.source_name = source_name

    def fetch(self) -> list[NewsItem]:
        try:
            feed = feedparser.parse(self.url)
            items = [
                NewsItem(
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    source=self.source_name,
                    summary=entry.get("summary", ""),
                    published=entry.get("published", ""),
                )
                for entry in feed.entries
            ]
            logger.info(f"Fetched {len(items)} items from {self.source_name}")
            return items
        except Exception as e:
            logger.error(f"Failed to fetch RSS from {self.source_name}: {e}")
            return []


class HNFetcher(BaseFetcher):
    def __init__(self, query: str = HN_QUERY, min_points: int = HN_MIN_POINTS):
        self.query = query
        self.min_points = min_points

    def fetch(self) -> list[NewsItem]:
        try:
            params = {
                "query": self.query,
                "tags": "story",
                "numericFilters": f"points>{self.min_points}",
            }
            response = httpx.get(HN_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            items = [
                NewsItem(
                    title=hit.get("title", ""),
                    url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    source="Hacker News",
                    summary="",
                    published=hit.get("created_at", ""),
                )
                for hit in data.get("hits", [])
            ]
            logger.info(f"Fetched {len(items)} items from HackerNews")
            return items
        except Exception as e:
            logger.error(f"Failed to fetch HN: {e}")
            return []


def fetch_all(fetchers: list[BaseFetcher] | None = None) -> list[NewsItem]:
    if fetchers is None:
        fetchers = [RSSFetcher(url, name) for url, name in RSS_SOURCES] + [HNFetcher()]

    all_items = []
    with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
        futures = [executor.submit(f.fetch) for f in fetchers]
        for future in as_completed(futures):
            all_items.extend(future.result())

    logger.info(f"Total items fetched: {len(all_items)}")
    return all_items
