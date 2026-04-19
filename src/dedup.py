import json
import logging

from src import NewsItem, HISTORY_PATH, MAX_HISTORY

logger = logging.getLogger(__name__)

# Load and Save

def load_history() -> set[str]:
    try:
        with open(HISTORY_PATH, "r") as f:
            return set(json.load(f))
    except Exception as e:
        logger.warning(f"Could not load history, starting fresh: {e}")
        return set()

def save_history(history: set[str]) -> None:
    try:
        trimmed = list(history)[-MAX_HISTORY:]
        with open(HISTORY_PATH, "w") as f:
            json.dump(trimmed, f)
        logger.info(f"History saved - {len(trimmed)} entries")
    except Exception as e:
        logger.error(f"Failed to save history: {e}")


# Dedup

def filter_seen(items: list[NewsItem]) -> tuple[list[NewsItem], set[str]]:
    history = load_history()

    new_items = [item for item in items if item.hash not in history]
    updated_history = history | {item.hash for item in new_items}

    logger.info(f"{len(new_items)} new items after dedup (filtered {len(items) - len(new_items)})")
    return new_items, updated_history