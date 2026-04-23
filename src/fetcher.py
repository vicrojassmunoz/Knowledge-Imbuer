import hashlib
import httpx
import feedparser
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel, computed_field

from src.config import HN_QUERY, HN_MIN_POINTS, HN_URL, RSS_SOURCES

logger = logging.getLogger(__name__)


# Data Model

class NewsItem(BaseModel):
    title: str
    url: str
    source: str
    summary: str=""
    published: str = ""
    one_liner: str = ""
    score: int = 0

    @computed_field
    @property
    def hash(self) -> str:
        return hashlib.md5(self.url.encode()).hexdigest()


# Fetchers

def fetch_rss(url:str, source_name:str) -> list[NewsItem]:
    try:
        feed = feedparser.parse(url)
        items = []

        for entry in feed.entries:
            item = NewsItem(
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                source=source_name,
                summary=entry.get("summary", ""),
                published=entry.get("published", ""),
            )
            items.append(item)

        logger.info(f"Fetched {len(items)} items from {source_name}")
        return items

    except Exception as e:
        logger.error(f"Failed to fetch RSS from {source_name}: {e}")
        return []


def fetch_hn(query: str = HN_QUERY, min_points: int = HN_MIN_POINTS) -> list[NewsItem]:
    try:
        params = {
            "query": query,
            "tags": "story",
            "numericFilters": f"points>{min_points}",
        }

        response = httpx.get(HN_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        items = []

        for hit in data.get("hits", []):
            item = NewsItem(
                title=hit.get("title", ""),
                url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                source="Hacker News",
                summary="",
                published=hit.get("created_at", ""),
            )
            items.append(item)

        logger.info(f"Fetched {len(items)} items from HackerNews")
        return items

    except Exception as e:
        logger.error(f"Failed to fetch HN: {e}")
        return []


# Orchestrator

def fetch_all() -> list[NewsItem]:
    all_items = []

    with ThreadPoolExecutor(max_workers=len(RSS_SOURCES) + 1) as executor:
        futures = [executor.submit(fetch_rss, url, name) for url, name in RSS_SOURCES]
        futures.append(executor.submit(fetch_hn))

        for future in as_completed(futures):
            all_items.extend(future.result())

    logger.info(f"Total items fetched: {len(all_items)}")
    return all_items
