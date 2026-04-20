import os
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime

# Set env vars before any src.* import so config.py reads them correctly
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("RESEND_API_KEY", "test-resend-key")
os.environ.setdefault("EMAIL_FROM", "test@example.com")
os.environ.setdefault("EMAIL_TO", "dest@example.com")
os.environ.setdefault("TELEGRAM_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "123456789")
os.environ.setdefault("SMTP_HOST", "smtp.example.com")
os.environ.setdefault("SMTP_USER", "user")
os.environ.setdefault("SMTP_PASS", "pass")

import pytest
from src.fetcher import NewsItem


@pytest.fixture
def make_item():
    """Factory for NewsItem with sensible defaults."""
    def _make(
        title="Open-source LLM benchmark released",
        url="https://example.com/article",
        source="Test Source",
        summary="",
        published="",
        one_liner="",
    ):
        return NewsItem(
            title=title,
            url=url,
            source=source,
            summary=summary,
            published=published,
            one_liner=one_liner,
        )
    return _make


@pytest.fixture
def recent_published():
    """RFC 2822 date string 1 hour ago."""
    dt = datetime.now(timezone.utc) - timedelta(hours=1)
    return format_datetime(dt)


@pytest.fixture
def old_published():
    """RFC 2822 date string well outside any max_age window."""
    return "Mon, 01 Jan 2001 00:00:00 +0000"
