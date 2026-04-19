import logging
import json

from groq import Groq

from src.config import GROQ_API_KEY, FILTER_MODEL, SYSTEM_PROMPT, FILTER_TEMPERATURE, FILTER_MAX_TOKENS
from src.fetcher import NewsItem

logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)


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

        if result.get("keep"):
            item.one_liner = result.get("one_liner", "")
            logger.info(f"KEPT [{result.get('score')}/10] {item.title[:60]}")
            return item

        logger.info(f" Dropped {item.title[:60]}")
        return None

    except Exception as e:
        logger.error(f"Failed to filter item '{item.title[:40]}': {e}")
        return None


def filter_all(items: list[NewsItem]) -> list[NewsItem]:
    results = []

    for item in items:
        filtered = filter_item(item)

        if filtered:
            results.append(filtered)

    logger.info(f"Filter complete — {len(results)}/{len(items)} items kept")
    return results
