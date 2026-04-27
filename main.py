import logging
from time import time

from src import setup_logging
from src.fetcher import fetch_all
from src.filter import filter_all, prefilter
from src.vector_store import filter_seen, save_items
from src.notifier import notify_all
from src.stats import RunStats, create_run, finish_run

setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    run_id = create_run()

    start = time()
    stats = RunStats()
    logger.info("Knowledge Imbuer starting...")
    logger.info(f"run_id from create_run: {run_id}")

    raw_items = fetch_all()
    stats.fetched = len(raw_items)
    stats.sources = {
        source: sum(1 for i in raw_items if i.source == source)
        for source in set(i.source for i in raw_items)
    }
    if not raw_items:
        logger.warning("No items fetched, aborting")
        return
    
    prefiltered_items = prefilter(raw_items, run_id=run_id)
    stats.after_prefilter = len(prefiltered_items)
    if not prefiltered_items:
        logger.info("No items passed prefilter, aborting")
        return

    new_items = filter_seen(prefiltered_items, run_id=run_id)
    stats.after_dedup = len(new_items)
    if not new_items:
        logger.info("No new items after dedup, aborting")
        return

    kept_items = filter_all(new_items, run_id=run_id)
    if not kept_items:
        logger.info("No items passed the filter, aborting")
        return

    if notify_all(kept_items):
        stats.delivered = len(kept_items)
        stats.duration_seconds = time() - start
        if run_id:
            finish_run(run_id, stats)
        save_items(kept_items, run_id=run_id)
        logger.info(
            f"Done — fetched {stats.fetched} → "
            f"prefilter {stats.after_prefilter} → "
            f"dedup {stats.after_dedup} → "
            f"delivered {stats.delivered} "
            f"({stats.duration_seconds:.1f}s)"
        )
    else:
        logger.error("Notification failed — history not saved to avoid losing items")


if __name__ == "__main__":
    main()