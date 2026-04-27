from unittest.mock import patch, ANY

import pytest

from src.fetcher import NewsItem
from main import main


def _item(url="https://example.com/a", one_liner="summary"):
    return NewsItem(title="LLM paper", url=url, source="S", one_liner=one_liner)


PATCH_FETCH = "main.fetch_all"
PATCH_PREFILTER = "main.prefilter"
PATCH_FILTER_SEEN = "main.filter_seen"
PATCH_FILTER_ALL = "main.filter_all"
PATCH_NOTIFY = "main.notify_all"
PATCH_SAVE = "main.save_items"
PATCH_CREATE_RUN = "main.create_run"
PATCH_FINISH_RUN = "main.finish_run"


class TestMainPipeline:
    def test_full_pipeline_success_saves_items(self):
        item = _item()

        with patch(PATCH_FETCH, return_value=[item]), \
             patch(PATCH_PREFILTER, return_value=[item]), \
             patch(PATCH_FILTER_SEEN, return_value=[item]), \
             patch(PATCH_FILTER_ALL, return_value=[item]), \
             patch(PATCH_NOTIFY, return_value=True), \
             patch(PATCH_SAVE) as mock_save, \
             patch(PATCH_CREATE_RUN), \
             patch(PATCH_FINISH_RUN):
            main()

        mock_save.assert_called_once_with([item], run_id=ANY)

    def test_does_not_save_items_when_notify_fails(self):
        item = _item()

        with patch(PATCH_FETCH, return_value=[item]), \
             patch(PATCH_PREFILTER, return_value=[item]), \
             patch(PATCH_FILTER_SEEN, return_value=[item]), \
             patch(PATCH_FILTER_ALL, return_value=[item]), \
             patch(PATCH_NOTIFY, return_value=False), \
             patch(PATCH_SAVE) as mock_save, \
             patch(PATCH_CREATE_RUN), \
             patch(PATCH_FINISH_RUN) as mock_finish_run:
            main()

        mock_save.assert_not_called()
        mock_finish_run.assert_not_called()

    def test_aborts_early_when_fetch_returns_empty(self):
        with patch(PATCH_FETCH, return_value=[]), \
             patch(PATCH_PREFILTER) as mock_prefilter, \
             patch(PATCH_FILTER_SEEN) as mock_dedup, \
             patch(PATCH_FILTER_ALL) as mock_filter, \
             patch(PATCH_NOTIFY) as mock_notify, \
             patch(PATCH_CREATE_RUN):
            main()

        mock_prefilter.assert_not_called()
        mock_dedup.assert_not_called()
        mock_filter.assert_not_called()
        mock_notify.assert_not_called()

    def test_aborts_when_no_items_pass_prefilter(self):
        item = _item()

        with patch(PATCH_FETCH, return_value=[item]), \
             patch(PATCH_PREFILTER, return_value=[]), \
             patch(PATCH_FILTER_SEEN) as mock_dedup, \
             patch(PATCH_FILTER_ALL) as mock_filter, \
             patch(PATCH_NOTIFY) as mock_notify, \
             patch(PATCH_CREATE_RUN):
            main()

        mock_dedup.assert_not_called()
        mock_filter.assert_not_called()
        mock_notify.assert_not_called()

    def test_aborts_when_no_new_items_after_dedup(self):
        item = _item()

        with patch(PATCH_FETCH, return_value=[item]), \
             patch(PATCH_PREFILTER, return_value=[item]), \
             patch(PATCH_FILTER_SEEN, return_value=[]), \
             patch(PATCH_FILTER_ALL) as mock_filter, \
             patch(PATCH_NOTIFY) as mock_notify, \
             patch(PATCH_CREATE_RUN):
            main()

        mock_filter.assert_not_called()
        mock_notify.assert_not_called()

    def test_aborts_when_no_items_pass_filter(self):
        item = _item()

        with patch(PATCH_FETCH, return_value=[item]), \
             patch(PATCH_PREFILTER, return_value=[item]), \
             patch(PATCH_FILTER_SEEN, return_value=[item]), \
             patch(PATCH_FILTER_ALL, return_value=[]), \
             patch(PATCH_NOTIFY) as mock_notify, \
             patch(PATCH_SAVE) as mock_save, \
             patch(PATCH_CREATE_RUN):
            main()

        mock_notify.assert_not_called()
        mock_save.assert_not_called()

    def test_pipeline_passes_correct_items_between_stages(self):
        raw = [_item(url="https://example.com/raw")]
        prefiltered = [_item(url="https://example.com/prefiltered")]
        deduped = [_item(url="https://example.com/deduped")]
        filtered = [_item(url="https://example.com/filtered")]

        with patch(PATCH_FETCH, return_value=raw), \
             patch(PATCH_PREFILTER, return_value=prefiltered) as mock_prefilter, \
             patch(PATCH_FILTER_SEEN, return_value=deduped) as mock_dedup, \
             patch(PATCH_FILTER_ALL, return_value=filtered) as mock_filter_all, \
             patch(PATCH_NOTIFY, return_value=True) as mock_notify, \
             patch(PATCH_SAVE) as mock_save, \
             patch(PATCH_CREATE_RUN), \
             patch(PATCH_FINISH_RUN):
            main()

        mock_prefilter.assert_called_once_with(raw, run_id=ANY)
        mock_dedup.assert_called_once_with(prefiltered, run_id=ANY)
        mock_filter_all.assert_called_once_with(deduped, run_id=ANY)
        mock_notify.assert_called_once_with(filtered)
        mock_save.assert_called_once_with(filtered, run_id=ANY)
