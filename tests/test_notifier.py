from unittest.mock import MagicMock, patch

import pytest

from src.fetcher import NewsItem
from src.notifier import notify_all, send_email, send_telegram, _format_telegram, _format_email


def _item(title="LLM paper", url="https://example.com", source="Test", one_liner="Summary here"):
    return NewsItem(title=title, url=url, source=source, one_liner=one_liner)


# ── Formatters ────────────────────────────────────────────────────────────────

class TestFormatTelegram:
    def test_contains_item_title(self):
        msg = _format_telegram([_item(title="My Article")])
        assert "My Article" in msg

    def test_contains_item_url(self):
        msg = _format_telegram([_item(url="https://example.com/specific")])
        assert "https://example.com/specific" in msg

    def test_escapes_html_in_title(self):
        msg = _format_telegram([_item(title="A <b>bold</b> claim")])
        assert "<b>bold</b>" not in msg
        assert "&lt;b&gt;" in msg

    def test_numbers_items(self):
        items = [_item(url=f"https://example.com/{i}") for i in range(3)]
        msg = _format_telegram(items)
        assert "1." in msg
        assert "2." in msg
        assert "3." in msg


class TestFormatEmail:
    def test_contains_item_title(self):
        html = _format_email([_item(title="Great Paper")])
        assert "Great Paper" in html

    def test_contains_item_url(self):
        html = _format_email([_item(url="https://papers.example.com")])
        assert "https://papers.example.com" in html

    def test_is_valid_html_structure(self):
        html = _format_email([_item()])
        assert "<html>" in html
        assert "</html>" in html


# ── send_telegram ─────────────────────────────────────────────────────────────

class TestSendTelegram:
    def test_returns_true_on_success(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        with patch("src.notifier.httpx.post", return_value=mock_resp):
            assert send_telegram([_item()]) is True

    def test_posts_to_correct_telegram_endpoint(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        with patch("src.notifier.httpx.post", return_value=mock_resp) as mock_post:
            send_telegram([_item()])
        url_called = mock_post.call_args[0][0]
        assert "api.telegram.org" in url_called
        assert "sendMessage" in url_called

    def test_returns_false_on_http_error(self):
        with patch("src.notifier.httpx.post", side_effect=Exception("connection refused")):
            assert send_telegram([_item()]) is False

    def test_returns_false_when_raise_for_status_fails(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")
        with patch("src.notifier.httpx.post", return_value=mock_resp):
            assert send_telegram([_item()]) is False


# ── send_email ────────────────────────────────────────────────────────────────

class TestSendEmail:
    def test_returns_true_on_success(self):
        with patch("src.notifier.resend.Emails.send", return_value={"id": "abc"}):
            assert send_email([_item()]) is True

    def test_calls_resend_with_correct_fields(self):
        with patch("src.notifier.resend.Emails.send") as mock_send:
            send_email([_item()])
        params = mock_send.call_args[0][0]
        assert "from" in params
        assert "to" in params
        assert "subject" in params
        assert "html" in params

    def test_returns_false_on_resend_exception(self):
        with patch("src.notifier.resend.Emails.send", side_effect=Exception("API error")):
            assert send_email([_item()]) is False


# ── notify_all ────────────────────────────────────────────────────────────────

class TestNotifyAll:
    def test_returns_true_when_both_succeed(self):
        with patch("src.notifier.send_telegram", return_value=True), \
             patch("src.notifier.send_email", return_value=True):
            assert notify_all([_item()]) is True

    def test_returns_false_when_telegram_fails(self):
        with patch("src.notifier.send_telegram", return_value=False), \
             patch("src.notifier.send_email", return_value=True):
            assert notify_all([_item()]) is False

    def test_returns_false_when_email_fails(self):
        with patch("src.notifier.send_telegram", return_value=True), \
             patch("src.notifier.send_email", return_value=False):
            assert notify_all([_item()]) is False

    def test_returns_true_and_skips_send_when_empty(self):
        with patch("src.notifier.send_telegram") as tg, \
             patch("src.notifier.send_email") as em:
            result = notify_all([])
        assert result is True
        tg.assert_not_called()
        em.assert_not_called()
