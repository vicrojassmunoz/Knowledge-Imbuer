from unittest.mock import patch, MagicMock

import pytest

from src.fetcher import NewsItem
from main import main


def _item(url="https://example.com/a", one_liner="summary"):
    return NewsItem(title="LLM paper", url=url, source="S", one_liner=one_liner)


PATCH_FETCH = "main.fetch_all"
PATCH_FILTER_SEEN = "main.filter_seen"
PATCH_FILTER_ALL = "main.filter_all"
PATCH_NOTIFY = "main.notify_all"
PATCH_SAVE = "main.save_history"


class TestMainPipeline:
    def test_full_pipeline_success_saves_history(self):
        item = _item()
        history = {item.hash}

        with patch(PATCH_FETCH, return_value=[item]), \
             patch(PATCH_FILTER_SEEN, return_value=([item], history)), \
             patch(PATCH_FILTER_ALL, return_value=[item]), \
             patch(PATCH_NOTIFY, return_value=True), \
             patch(PATCH_SAVE) as mock_save:
            main()

        mock_save.assert_called_once_with(history)

    def test_does_not_save_history_when_notify_fails(self):
        item = _item()
        history = {item.hash}

        with patch(PATCH_FETCH, return_value=[item]), \
             patch(PATCH_FILTER_SEEN, return_value=([item], history)), \
             patch(PATCH_FILTER_ALL, return_value=[item]), \
             patch(PATCH_NOTIFY, return_value=False), \
             patch(PATCH_SAVE) as mock_save:
            main()

        mock_save.assert_not_called()

    def test_aborts_early_when_fetch_returns_empty(self):
        with patch(PATCH_FETCH, return_value=[]), \
             patch(PATCH_FILTER_SEEN) as mock_dedup, \
             patch(PATCH_FILTER_ALL) as mock_filter, \
             patch(PATCH_NOTIFY) as mock_notify:
            main()

        mock_dedup.assert_not_called()
        mock_filter.assert_not_called()
        mock_notify.assert_not_called()

    def test_aborts_when_no_new_items_after_dedup(self):
        item = _item()

        with patch(PATCH_FETCH, return_value=[item]), \
             patch(PATCH_FILTER_SEEN, return_value=([], {item.hash})), \
             patch(PATCH_FILTER_ALL) as mock_filter, \
             patch(PATCH_NOTIFY) as mock_notify:
            main()

        mock_filter.assert_not_called()
        mock_notify.assert_not_called()

    def test_aborts_when_no_items_pass_filter(self):
        item = _item()

        with patch(PATCH_FETCH, return_value=[item]), \
             patch(PATCH_FILTER_SEEN, return_value=([item], {item.hash})), \
             patch(PATCH_FILTER_ALL, return_value=[]), \
             patch(PATCH_NOTIFY) as mock_notify, \
             patch(PATCH_SAVE) as mock_save:
            main()

        mock_notify.assert_not_called()
        mock_save.assert_not_called()

    def test_pipeline_passes_correct_items_between_stages(self):
        raw = [_item(url="https://example.com/raw")]
        deduped = [_item(url="https://example.com/deduped")]
        filtered = [_item(url="https://example.com/filtered")]
        history = {"somehash"}

        with patch(PATCH_FETCH, return_value=raw), \
             patch(PATCH_FILTER_SEEN, return_value=(deduped, history)) as mock_dedup, \
             patch(PATCH_FILTER_ALL, return_value=filtered) as mock_filter_all, \
             patch(PATCH_NOTIFY, return_value=True) as mock_notify, \
             patch(PATCH_SAVE):
            main()

        mock_dedup.assert_called_once_with(raw)
        mock_filter_all.assert_called_once_with(deduped)
        mock_notify.assert_called_once_with(filtered)
