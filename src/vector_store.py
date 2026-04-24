import logging
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY
from src.fetcher import NewsItem

logger = logging.getLogger(__name__)


model = SentenceTransformer("all-MiniLM-L6-v2")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def _get_seen_hashes(hashes: list[str], chunk_size: int = 200) -> set[str]:
    seen = set()
    for i in range(0, len(hashes), chunk_size):
        chunk = hashes[i:i + chunk_size]
        try:
            result = supabase.table("items").select("hash").in_("hash", chunk).execute()
            seen.update(row["hash"] for row in result.data)
        except Exception as e:
            logger.error(f"Failed to check hashes chunk {i}: {e}")
    return seen

def embed(text: str) -> list[float]:
    return model.encode(text).tolist()


def is_seen(item: NewsItem) -> bool | None:
    try:
        result = supabase.table("items").select("hash").eq("hash", item.hash).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"Failed to check hash for: {item.title[:40]}: {e}")

def is_similar(item: NewsItem, threshold: float=0.8) -> bool:
    try:
        embedding = embed(f"{item.title} {item.summary}")
        result = supabase.rpc("match_items", {
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": 1,
        }).execute()
        return len(result.data) > 0

    except Exception as e:
        logger.error(f"Failed to check similarity for: {item.title[:40]}: {e}")
        return False

def save_item(item: NewsItem) -> None:
    try:
        embedding = embed(f"{item.title} {item.summary}")
        supabase.table("items").insert({
            "hash": item.hash,
            "title": item.title,
            "url": item.url,
            "source": item.source,
            "one_liner": item.one_liner,
            "score": item.score,
            "published": item.published,
            "embedding": embedding,
        }).execute()
    except Exception as e:
        logger.error(f"Failed to save item '{item.title[:40]}': {e}")

def filter_seen(items: list[NewsItem]) -> list[NewsItem]:
    all_hashes = [item.hash for item in items]
    seen_hashes = _get_seen_hashes(all_hashes)

    candidates = [item for item in items if item.hash not in seen_hashes]
    logger.info(f"Exact dedup: {len(candidates)}/{len(items)} items remaining")

    new_items = []
    for item in candidates:
        if is_similar(item):
            logger.info(f"Semantic duplicate dropped: {item.title[:60]}")
            continue
        new_items.append(item)

    logger.info(f"{len(new_items)} new items after dedup (filtered {len(items) - len(new_items)})")
    return new_items

def save_items(items: list[NewsItem]) -> None:
    for item in items:
        save_item(item)
    logger.info(f"Saved {len(items)} items to Supabase")
