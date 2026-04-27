import logging
from datetime import datetime, timezone
from pydantic import BaseModel

from src.vector_store import get_client

logger = logging.getLogger(__name__)

class RunStats(BaseModel):
    fetched: int = 0
    after_prefilter: int = 0
    after_dedup: int = 0
    delivered: int = 0
    duration_seconds: float = 0.0
    sources: dict[str, int] = {}


def save_run(stats: RunStats, run_id: str | None = None) -> str | None:
    try:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **stats.model_dump()
        }
        if run_id:
            payload["id"] = run_id
        result = get_client().table("runs").insert(payload).execute()
        logger.info("Run stats saved to Supabase")
        return result.data[0]["id"]
    except Exception as e:
        logger.error(f"Failed to save run stats: {e}")

def fetch_recent_runs(limit: int = 14) -> list[dict]:
    try:
        result = (
            get_client()
            .table("runs")
            .select("*")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    except Exception as e:
        logger.error(f"Failed to fetch recent runs: {e}")
        return []
