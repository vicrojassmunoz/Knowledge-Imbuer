import json
from unittest.mock import mock_open, patch

import pytest

from src.dedup import filter_seen, load_history, save_history
from src.fetcher import NewsItem


def _item(url: str) -> NewsItem:
    return NewsItem(title="T", url=url, source="S")


class TestLoadHistory:
    def test_returns_set_of_hashes(self):
        hashes = ["abc123", "def456"]
        with patch("builtins.open", mock_open(read_data=json.dumps(hashes))):
            result = load_history()
        assert result == set(hashes)

    def test_returns_empty_set_on_missing_file(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = load_history()
        assert result == set()

    def test_returns_empty_set_on_corrupt_file(self):
        with patch("builtins.open", mock_open(read_data="not json")):
            result = load_history()
        assert result == set()


class TestSaveHistory:
    def test_writes_trimmed_list_as_json(self):
        m = mock_open()
        with patch("builtins.open", m):
            save_history({"h1", "h2"})
        written = "".join(call.args[0] for call in m().write.call_args_list)
        data = json.loads(written)
        assert set(data) == {"h1", "h2"}

    def test_silently_handles_write_error(self):
        with patch("builtins.open", side_effect=PermissionError("denied")):
            save_history({"h1"})  # must not raise


class TestFilterSeen:
    def test_removes_items_in_history(self):
        item = _item("https://example.com/old")
        with patch("src.dedup.load_history", return_value={item.hash}):
            new_items, _ = filter_seen([item])
        assert new_items == []

    def test_keeps_items_not_in_history(self):
        item = _item("https://example.com/new")
        with patch("src.dedup.load_history", return_value=set()):
            new_items, _ = filter_seen([item])
        assert new_items == [item]

    def test_partial_dedup(self):
        seen = _item("https://example.com/seen")
        fresh = _item("https://example.com/fresh")
        with patch("src.dedup.load_history", return_value={seen.hash}):
            new_items, _ = filter_seen([seen, fresh])
        assert new_items == [fresh]

    def test_updated_history_includes_new_hashes(self):
        item = _item("https://example.com/new")
        with patch("src.dedup.load_history", return_value=set()):
            _, updated = filter_seen([item])
        assert item.hash in updated

    def test_updated_history_preserves_existing_hashes(self):
        existing_hash = "existing_abc"
        item = _item("https://example.com/new")
        with patch("src.dedup.load_history", return_value={existing_hash}):
            _, updated = filter_seen([item])
        assert existing_hash in updated

    def test_empty_input_returns_empty(self):
        with patch("src.dedup.load_history", return_value=set()):
            new_items, updated = filter_seen([])
        assert new_items == []
        assert updated == set()
