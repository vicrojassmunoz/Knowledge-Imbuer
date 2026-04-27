import logging
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY
from src.fetcher import NewsItem

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None
_supabase: Client | None = None

def get_client() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

def _get_seen_hashes(hashes: list[str], chunk_size: int = 200) -> set[str]:
    seen = set()
    for i in range(0, len(hashes), chunk_size):
        chunk = hashes[i:i + chunk_size]
        try:
            result = get_client().table("items").select("hash").in_("hash", chunk).execute()
            seen.update(row["hash"] for row in result.data)
        except Exception as e:
            logger.error(f"Failed to check hashes chunk {i}: {e}")
    return seen



def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(text: str) -> list[float]:
    return _get_model().encode(text).tolist()


def is_similar(item: NewsItem, threshold: float=0.8) -> bool:
    try:
        embedding = embed(f"{item.title} {item.summary}")
        result = get_client().rpc("match_items", {
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": 1,
        }).execute()
        return len(result.data) > 0

    except Exception as e:
        logger.error(f"Failed to check similarity for: {item.title[:40]}: {e}")
        return False

def save_item(item: NewsItem, run_id: str | None = None) -> None:
    try:
        embedding = embed(f"{item.title} {item.summary}")
        payload = {
            "hash": item.hash,
            "title": item.title,
            "url": item.url,
            "source": item.source,
            "one_liner": item.one_liner,
            "score": item.score,
            "published": item.published,
            "embedding": embedding,
        }
        if run_id is not None:
            payload["run_id"] = run_id
        get_client().table("items").insert(payload).execute()
    except Exception as e:
        logger.error(f"Failed to save item '{item.title[:40]}': {e}")

def filter_seen(items: list[NewsItem], run_id: str | None = None) -> list[NewsItem]:
    all_hashes = [item.hash for item in items]
    seen_hashes = _get_seen_hashes(all_hashes)

    candidates = [item for item in items if item.hash not in seen_hashes]
    exact_dupes = [item for item in items if item.hash in seen_hashes]
    if run_id and exact_dupes:
        save_discarded(exact_dupes, "exact_dedup", run_id)
    logger.info(f"Exact dedup: {len(candidates)}/{len(items)} items remaining")

    new_items = []
    semantic_dupes = []
    for item in candidates:
        if is_similar(item):
            logger.info(f"Semantic duplicate dropped: {item.title[:60]}")
            semantic_dupes.append(item)
            continue
        new_items.append(item)

    if run_id and semantic_dupes:
        save_discarded(semantic_dupes, "semantic_dedup", run_id)

    logger.info(f"{len(new_items)} new items after dedup (filtered {len(items) - len(new_items)})")
    return new_items

def save_items(items: list[NewsItem], run_id: str | None = None) -> None:
    for item in items:
        save_item(item, run_id=run_id)
    logger.info(f"Saved {len(items)} items to Supabase")

def save_discarded(items: list[NewsItem], reason: str, run_id: str | None = None) -> None:
    try:
        payload = [
            {
                "run_id": run_id,
                "title": item.title,
                "url": item.url,
                "source": item.source,
                "reason": reason,
                "score": item.score,
            }
            for item in items
        ]
        get_client().table("discarded_items").insert(payload).execute()
        logger.debug(f"Saved {len(payload)} discarded items (reason: {reason})")
    except Exception as e:
        logger.error(f"Failed to save discarded items: {e}")
