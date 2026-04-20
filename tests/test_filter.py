from unittest.mock import MagicMock, patch

import pytest

from src.fetcher import NewsItem
from src.filter import _is_recent, filter_all, filter_item, prefilter
from src.config import PREFILTER_MAX_AGE_HOURS


def _item(title="", summary="", published="", url="https://example.com/x") -> NewsItem:
    return NewsItem(title=title, url=url, source="S", summary=summary, published=published)


# ── _is_recent ────────────────────────────────────────────────────────────────

class TestIsRecent:
    def test_empty_published_is_considered_recent(self):
        assert _is_recent(_item(published=""), PREFILTER_MAX_AGE_HOURS) is True

    def test_clearly_old_date_is_not_recent(self):
        assert _is_recent(_item(published="Mon, 01 Jan 2001 00:00:00 +0000"), PREFILTER_MAX_AGE_HOURS) is False

    def test_recent_date_is_recent(self, recent_published):
        assert _is_recent(_item(published=recent_published), PREFILTER_MAX_AGE_HOURS) is True

    def test_unparseable_date_is_treated_as_recent(self):
        assert _is_recent(_item(published="not-a-date"), PREFILTER_MAX_AGE_HOURS) is True


# ── prefilter ─────────────────────────────────────────────────────────────────

class TestPrefilter:
    def test_keeps_item_with_keyword_in_title(self, recent_published):
        item = _item(title="New LLM benchmark released", published=recent_published)
        result = prefilter([item])
        assert item in result

    def test_keeps_item_with_keyword_in_summary(self, recent_published):
        item = _item(title="Interesting post", summary="transformer architecture paper", published=recent_published)
        result = prefilter([item])
        assert item in result

    def test_drops_item_with_no_keyword(self, recent_published):
        item = _item(title="Weekend sports recap", summary="goals and highlights", published=recent_published)
        result = prefilter([item])
        assert item not in result

    def test_drops_blacklisted_item(self, recent_published):
        item = _item(title="We are hiring ML engineers", summary="llm", published=recent_published)
        result = prefilter([item])
        assert item not in result

    def test_drops_old_item_even_with_keyword(self, old_published):
        item = _item(title="New LLM paper", published=old_published)
        result = prefilter([item])
        assert item not in result

    def test_keyword_matching_is_case_insensitive(self, recent_published):
        item = _item(title="TRANSFORMER Model Analysis", published=recent_published)
        result = prefilter([item])
        assert item in result

    def test_returns_empty_for_empty_input(self):
        assert prefilter([]) == []


# ── filter_item ───────────────────────────────────────────────────────────────

class TestFilterItem:
    def _mock_groq_response(self, content: str):
        choice = MagicMock()
        choice.message.content = content
        response = MagicMock()
        response.choices = [choice]
        return response

    def test_keeps_item_when_keep_true_and_score_above_threshold(self):
        payload = '{"keep": true, "score": 9, "one_liner": "Fast open-source LLM inference engine"}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_groq_response(payload)

        with patch("src.filter.client", mock_client):
            result = filter_item(_item(title="llm.c repo"))

        assert result is not None
        assert result.one_liner == "Fast open-source LLM inference engine"

    def test_drops_item_when_keep_false(self):
        payload = '{"keep": false, "score": 3, "one_liner": ""}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_groq_response(payload)

        with patch("src.filter.client", mock_client):
            result = filter_item(_item(title="Hiring ML engineers"))

        assert result is None

    def test_drops_item_when_score_below_min(self):
        payload = '{"keep": true, "score": 2, "one_liner": "meh"}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_groq_response(payload)

        with patch("src.filter.client", mock_client):
            result = filter_item(_item(title="Some weak post"))

        assert result is None

    def test_strips_think_tags_from_reasoning_model_output(self):
        payload = '<think>reasoning here</think>\n{"keep": true, "score": 8, "one_liner": "Good paper"}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_groq_response(payload)

        with patch("src.filter.client", mock_client):
            result = filter_item(_item(title="Research paper"))

        assert result is not None
        assert result.one_liner == "Good paper"

    def test_returns_none_on_groq_exception(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")

        with patch("src.filter.client", mock_client):
            result = filter_item(_item(title="anything"))

        assert result is None

    def test_returns_none_on_invalid_json(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_groq_response("not json at all")

        with patch("src.filter.client", mock_client):
            result = filter_item(_item(title="anything"))

        assert result is None


# ── filter_all ────────────────────────────────────────────────────────────────

class TestFilterAll:
    def test_returns_only_kept_items(self, recent_published):
        kept = _item(title="LLM research paper", published=recent_published, url="https://example.com/kept")
        dropped = _item(title="Hiring post llm", published=recent_published, url="https://example.com/dropped")

        keep_response = MagicMock()
        keep_response.choices[0].message.content = '{"keep": true, "score": 9, "one_liner": "good"}'
        drop_response = MagicMock()
        drop_response.choices[0].message.content = '{"keep": false, "score": 2, "one_liner": ""}'

        def side_effect(model, messages, temperature, max_tokens):
            title = messages[1]["content"].split("\n")[0].replace("Title: ", "")
            if title == kept.title:
                return keep_response
            return drop_response

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = side_effect

        with patch("src.filter.client", mock_client):
            results = filter_all([kept, dropped])

        assert len(results) == 1
        assert results[0].title == kept.title

    def test_returns_empty_when_all_prefiltered_out(self, old_published):
        items = [_item(title="Sports news", published=old_published)]
        mock_client = MagicMock()
        with patch("src.filter.client", mock_client):
            results = filter_all(items)
        mock_client.chat.completions.create.assert_not_called()
        assert results == []
