import logging

from src.config import setup_logging
from src.fetcher import fetch_all
from src.filter import filter_all
from src.dedup import filter_seen, save_history
from src.notifier import notify_all

setup_logging()
logger = logging.getLogger(__name__)

def main():
    logger.info('Knowledge Imbuer starting')

    raw_items = fetch_all()
    if not raw_items:
        logger.warning("No items found, aborting.")
        return

    new_items, updated_history = filter_seen(raw_items)
    if not new_items:
        logger.warning("No new items found, aborting.")
        return

    kept_items = filter_all(new_items)
    if not kept_items:
        logger.warning("No items passed the filter, aborting.")
        return

    success = notify_all(kept_items)

    if success:
        save_history(updated_history)
        logger.info(f"Done — {len(kept_items)} items delivered and history updated")
    else:
        logger.error("Notification failed - history not saved to avoid losing items")

if __name__ == "__main__":
    main()
