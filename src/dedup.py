import json
import logging

from src.config import HISTORY_PATH, MAX_HISTORY
from src.fetcher import NewsItem

logger = logging.getLogger(__name__)


def load_history() -> set[str]:
    try:
        with open(HISTORY_PATH, "r") as f:
            return set(json.load(f))
    except Exception as e:
        logger.warning(f"Could not load history, starting fresh: {e}")
        return set()

def save_history(history: set[str]) -> None:
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        trimmed = list(history)[-MAX_HISTORY:]
        with open(HISTORY_PATH, "w") as f:
            json.dump(trimmed, f)
        logger.info(f"History saved - {len(trimmed)} entries")
    except Exception as e:
        logger.error(f"Failed to save history: {e}")


def filter_seen(items: list[NewsItem]) -> tuple[list[NewsItem], set[str]]:
    history = load_history()

    new_items = [item for item in items if item.hash not in history]
    updated_history = history | {item.hash for item in new_items}

    logger.info(f"{len(new_items)} new items after dedup (filtered {len(items) - len(new_items)})")
    return new_items, updated_history