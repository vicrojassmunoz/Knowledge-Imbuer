from unittest.mock import MagicMock, patch

import pytest

from src.fetcher import NewsItem
from src.notifier import (
    BaseNotifier,
    TelegramNotifier,
    ResendEmailNotifier,
    notify_all,
)


def _item(title="LLM paper", url="https://example.com", source="Test", one_liner="Summary here"):
    return NewsItem(title=title, url=url, source=source, one_liner=one_liner)


# ── Formatters ────────────────────────────────────────────────────────────────

class TestTelegramNotifierFormat:
    def test_contains_item_title(self):
        msg = TelegramNotifier().format([_item(title="My Article")])
        assert "My Article" in msg

    def test_contains_item_url(self):
        msg = TelegramNotifier().format([_item(url="https://example.com/specific")])
        assert "https://example.com/specific" in msg

    def test_escapes_html_in_title(self):
        msg = TelegramNotifier().format([_item(title="A <b>bold</b> claim")])
        assert "<b>bold</b>" not in msg
        assert "&lt;b&gt;" in msg

    def test_numbers_items(self):
        items = [_item(url=f"https://example.com/{i}") for i in range(3)]
        msg = TelegramNotifier().format(items)
        assert "1." in msg
        assert "2." in msg
        assert "3." in msg

    def test_escapes_ampersand_in_url(self):
        # URLs with & in query params caused a 400 Bad Request from Telegram
        # because the HTML parser rejected unescaped & inside href attributes.
        url = "https://arxiv.org/search/?searchtype=all&query=qwen3&start=0"
        msg = TelegramNotifier().format([_item(url=url)])
        assert "&query=" not in msg
        assert "&amp;query=" in msg

    def test_notify_passes_with_ampersand_url(self):
        # Regression: TelegramNotifier must not raise or return False when the
        # URL contains & characters (previously caused Telegram 400 Bad Request).
        url = "https://arxiv.org/search/?searchtype=all&query=qwen3&start=0"
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        with patch("src.notifier.httpx.post", return_value=mock_resp) as mock_post:
            result = TelegramNotifier().notify([_item(url=url)])
        assert result is True
        payload = mock_post.call_args[1]["json"]
        assert "&amp;" in payload["text"]
        assert "&query=" not in payload["text"]


class TestResendEmailNotifierFormat:
    def test_contains_item_title(self):
        output = ResendEmailNotifier().format([_item(title="Great Paper")])
        assert "Great Paper" in output

    def test_contains_item_url(self):
        output = ResendEmailNotifier().format([_item(url="https://papers.example.com")])
        assert "https://papers.example.com" in output

    def test_is_valid_html_structure(self):
        output = ResendEmailNotifier().format([_item()])
        assert "<html>" in output
        assert "</html>" in output


# ── TelegramNotifier ──────────────────────────────────────────────────────────

class TestTelegramNotifier:
    def test_returns_true_on_success(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        with patch("src.notifier.httpx.post", return_value=mock_resp):
            assert TelegramNotifier().notify([_item()]) is True

    def test_posts_to_correct_telegram_endpoint(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        with patch("src.notifier.httpx.post", return_value=mock_resp) as mock_post:
            TelegramNotifier().notify([_item()])
        url_called = mock_post.call_args[0][0]
        assert "api.telegram.org" in url_called
        assert "sendMessage" in url_called

    def test_returns_false_on_http_error(self):
        with patch("src.notifier.httpx.post", side_effect=Exception("connection refused")):
            assert TelegramNotifier().notify([_item()]) is False

    def test_returns_false_when_raise_for_status_fails(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")
        with patch("src.notifier.httpx.post", return_value=mock_resp):
            assert TelegramNotifier().notify([_item()]) is False


# ── ResendEmailNotifier ───────────────────────────────────────────────────────

class TestResendEmailNotifier:
    def test_returns_true_on_success(self):
        with patch("src.notifier.resend.Emails.send", return_value={"id": "abc"}):
            assert ResendEmailNotifier().notify([_item()]) is True

    def test_calls_resend_with_correct_fields(self):
        with patch("src.notifier.resend.Emails.send") as mock_send:
            ResendEmailNotifier().notify([_item()])
        params = mock_send.call_args[0][0]
        assert "from" in params
        assert "to" in params
        assert "subject" in params
        assert "html" in params

    def test_returns_false_on_resend_exception(self):
        with patch("src.notifier.resend.Emails.send", side_effect=Exception("API error")):
            assert ResendEmailNotifier().notify([_item()]) is False


# ── notify_all ────────────────────────────────────────────────────────────────

class TestNotifyAll:
    def test_returns_true_when_both_succeed(self):
        mock_tg = MagicMock(spec=BaseNotifier)
        mock_tg.notify.return_value = True
        mock_email = MagicMock(spec=BaseNotifier)
        mock_email.notify.return_value = True
        assert notify_all([_item()], notifiers=[mock_tg, mock_email]) is True

    def test_returns_false_when_telegram_fails(self):
        mock_tg = MagicMock(spec=BaseNotifier)
        mock_tg.notify.return_value = False
        mock_email = MagicMock(spec=BaseNotifier)
        mock_email.notify.return_value = True
        assert notify_all([_item()], notifiers=[mock_tg, mock_email]) is False

    def test_returns_false_when_email_fails(self):
        mock_tg = MagicMock(spec=BaseNotifier)
        mock_tg.notify.return_value = True
        mock_email = MagicMock(spec=BaseNotifier)
        mock_email.notify.return_value = False
        assert notify_all([_item()], notifiers=[mock_tg, mock_email]) is False

    def test_returns_true_and_skips_send_when_empty(self):
        mock_tg = MagicMock(spec=BaseNotifier)
        mock_email = MagicMock(spec=BaseNotifier)
        result = notify_all([], notifiers=[mock_tg, mock_email])
        assert result is True
        mock_tg.notify.assert_not_called()
        mock_email.notify.assert_not_called()
