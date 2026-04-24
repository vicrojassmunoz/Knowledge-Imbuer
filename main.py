import logging
from time import time

from src import setup_logging
from src.fetcher import fetch_all
from src.filter import filter_all, prefilter
from src.vector_store import filter_seen, save_items
from src.notifier import TelegramNotifier, ResendEmailNotifier

setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    start = time()
    logger.info("Knowledge Imbuer starting...")

    raw_items = fetch_all()
    if not raw_items:
        logger.warning("No items fetched, aborting")
        return

    prefiltered_items = prefilter(raw_items)
    if not prefiltered_items:
        logger.info("No items passed prefilter, aborting")
        return

    new_items = filter_seen(prefiltered_items)
    if not new_items:
        logger.info("No new items after dedup, aborting")
        return


    kept_items = filter_all(new_items)
    if not kept_items:
        logger.info("No items passed the filter, aborting")
        return


    notifiers = [TelegramNotifier(), ResendEmailNotifier()]
    success = all(n.notify(kept_items) for n in notifiers)


    if success:
        save_items(kept_items)
        duration = time() - start
        logger.info(f"Done — {len(kept_items)} items delivered in {duration:.1f}s")
    else:
        logger.error("Notification failed — items not saved to avoid losing them")


if __name__ == "__main__":
    main()