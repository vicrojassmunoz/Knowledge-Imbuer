import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

from groq import Groq
from tqdm import tqdm

from src.config import (GROQ_API_KEY,
                        FILTER_MODEL,
                        SYSTEM_PROMPT,
                        FILTER_TEMPERATURE,
                        FILTER_MAX_TOKENS,
                        FILTER_MAX_INPUT,
                        FILTER_MIN_SCORE,
                        FILTER_MAX_WORKERS,
                        PREFILTER_KEYWORDS,
                        PREFILTER_BLACKLIST,
                        PREFILTER_MAX_AGE_HOURS)
from src.fetcher import NewsItem

logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY) # TODO: Interface for clients


def _is_recent(item: NewsItem, max_age_hours:int) -> bool:
    if not item.published:
        return True

    try:
        published = parsedate_to_datetime(item.published)
        curoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        return published >= curoff

    except Exception as e:
        logger.warning(f"Failed to parse date '{item.published}'")
        return True


def prefilter(items: list[NewsItem]) -> list[NewsItem]:
    result = []
    for item in tqdm(items, desc="Prefiltering", unit="item"):
        text = (item.title + " " + item.summary).lower()
        if not _is_recent(item, PREFILTER_MAX_AGE_HOURS):
            continue
        if any(kw in text for kw in PREFILTER_BLACKLIST):
            continue
        if any(kw in text for kw in PREFILTER_KEYWORDS):
            result.append(item)

    logger.info(f"Prefilter: {len(result)}/{len(items)} items passed")
    return result

def filter_item(item:NewsItem) -> NewsItem | None:
    try:
        user_message = f"Title: {item.title}\nSummary: {item.summary}\nSource: {item.source}"

        response = client.chat.completions.create(
            model=FILTER_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=FILTER_TEMPERATURE,
            max_tokens=FILTER_MAX_TOKENS
        )

        raw = response.choices[0].message.content
        if "</think>" in raw:
            raw = raw.split("</think>")[-1].strip()
        logger.debug(f"Raw message: {raw}")
        result = json.loads(raw)

        if result.get("keep") and result.get("score", 0 ) >= FILTER_MIN_SCORE:
            item.one_liner = result.get("one_liner", "")
            logger.info(f"KEPT [{result.get('score')}/10] {item.title[:60]}")
            return item

        logger.info(f" Dropped {item.title[:60]}")
        return None

    except Exception as e:
        logger.error(f"Failed to filter item '{item.title[:40]}': {e}")
        return None


def filter_all(items: list[NewsItem]) -> list[NewsItem]:

    prefiltered = prefilter(items)

    limited = prefiltered[:FILTER_MAX_INPUT]
    logger.info(f"Sending {len(limited)} items to LLM filter")
    results = []

    with ThreadPoolExecutor(max_workers=FILTER_MAX_WORKERS) as executor:
        futures = {executor.submit(filter_item, item): item for item in limited}
        for future in tqdm(as_completed(futures), total=len(futures), desc="LLM Filtering", unit="item"):
            result = future.result()
            if result:
                results.append(result)

    logger.info(f"Filter complete — {len(results)}/{len(limited)} items kept")
    return results
