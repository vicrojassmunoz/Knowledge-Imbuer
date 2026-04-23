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

import pytest


@pytest.fixture
def recent_published():
    """RFC 2822 date string 1 hour ago."""
    dt = datetime.now(timezone.utc) - timedelta(hours=1)
    return format_datetime(dt)


@pytest.fixture
def old_published():
    """RFC 2822 date string well outside any max_age window."""
    return "Mon, 01 Jan 2001 00:00:00 +0000"
