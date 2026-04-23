import hashlib
import httpx
import feedparser
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel, computed_field

from src.config import (HN_QUERY,
                        HN_MIN_POINTS,
                        HN_URL,
                        RSS_SOURCES,
                        REDDIT_BASE_URL,
                        REDDIT_SUBREDDITS,
                        REDDIT_MAX_RESULTS,
                        REDDIT_MIN_UPVOTES)

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

class RedditFetcher(BaseFetcher):
    def __init__(self,
                 subreddit: str,
                 sort: str = "hot",
                 min_upvotes: int = REDDIT_MIN_UPVOTES,
                 max_results: int = REDDIT_MAX_RESULTS
                 ):
        self.subreddit = subreddit
        self.sort = sort
        self.min_upvotes = min_upvotes
        self.max_results = max_results

    def fetch(self) -> list[NewsItem]:
        try:
            url = f"{REDDIT_BASE_URL}/r/{self.subreddit}/{self.sort}.json"
            headers = {"User-Agent": "Prometheus"}
            params = {"limit": self.max_results}
            if self.sort == "top":
                params["t"] = "day"

            response = httpx.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            items = []

            for post in data["data"]["children"]:
                post_data = post["data"]

                if post_data.get("ups", 0) < self.min_upvotes:
                    continue
                if post_data.get("its_self") and not post_data.get("selftext"):
                    continue
                if post_data.get("title", "").startswith("[D]"):
                    continue

                item = NewsItem(
                    title=post_data.get("title", ""),
                    url=post_data.get("url") or f"https://reddit.com{post_data.get('permalink')}",
                    source=f"r/{self.subreddit}",
                    summary=post_data.get("selftext", "")[500:],
                    published=str(post_data.get("created_utc", "")),
                )
                items.append(item)
            logger.info(f"Fetched {len(items)} items from r/{self.subreddit}")
            return items

        except Exception as e:
            logger.error(f"Failed to fetch r/{self.subreddit}: {e}")
            return []

def fetch_all(fetchers: list[BaseFetcher] | None = None) -> list[NewsItem]:
    if fetchers is None:
        fetchers = ([RSSFetcher(url, name) for url, name in RSS_SOURCES] +
                    [HNFetcher()] +
                    [RedditFetcher(s["name"], s["sort"]) for s in REDDIT_SUBREDDITS]
                    )

    all_items = []
    with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
        futures = [executor.submit(f.fetch) for f in fetchers]
        for future in as_completed(futures):
            all_items.extend(future.result())

    logger.info(f"Total items fetched: {len(all_items)}")
    return all_items
