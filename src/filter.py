import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from groq import Groq

from src.config import GROQ_API_KEY, FILTER_MODEL, SYSTEM_PROMPT, FILTER_TEMPERATURE, FILTER_MAX_TOKENS, FILTER_MAX_INPUT, FILTER_MIN_SCORE
from src.fetcher import NewsItem

logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY) # TODO: Interface for clients


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
    limited = items[:FILTER_MAX_INPUT]
    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(filter_item, item): item for item in limited}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    logger.info(f"Filter complete — {len(results)}/{len(limited)} items kept")
    return results
