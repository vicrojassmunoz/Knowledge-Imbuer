from unittest.mock import MagicMock, patch

import pytest

from src.stats import RunStats, fetch_recent_runs, create_run, finish_run

PATCH_CLIENT = "src.stats.get_client"


class TestRunStats:
    def test_default_values(self):
        s = RunStats()
        assert s.fetched == 0
        assert s.after_prefilter == 0
        assert s.after_dedup == 0
        assert s.delivered == 0
        assert s.duration_seconds == 0.0
        assert s.sources == {}

    def test_model_dump_includes_all_fields(self):
        s = RunStats(fetched=10, after_prefilter=8, after_dedup=6, delivered=3,
                     duration_seconds=1.5, sources={"arxiv": 5, "hn": 5})
        d = s.model_dump()
        assert d["fetched"] == 10
        assert d["after_prefilter"] == 8
        assert d["after_dedup"] == 6
        assert d["delivered"] == 3
        assert d["duration_seconds"] == 1.5
        assert d["sources"] == {"arxiv": 5, "hn": 5}


class TestCreateRun:
    def _mock_client(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        return client

    def test_inserts_row_with_timestamp(self):
        client = self._mock_client()

        with patch(PATCH_CLIENT, return_value=client):
            create_run()

        client.table.assert_called_once_with("runs")
        insert_call = client.table.return_value.insert.call_args[0][0]
        assert "timestamp" in insert_call

    def test_returns_id_from_response(self):
        client = self._mock_client()
        client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "abc-123"}]

        with patch(PATCH_CLIENT, return_value=client):
            result = create_run()

        assert result == "abc-123"

    def test_does_not_raise_on_supabase_error(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.side_effect = Exception("db error")

        with patch(PATCH_CLIENT, return_value=client):
            create_run()  # must not raise


class TestFinishRun:
    def test_updates_row_with_stats(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        stats = RunStats(fetched=5, after_prefilter=4, after_dedup=3, delivered=2,
                         duration_seconds=9.9, sources={"hn": 5})

        with patch(PATCH_CLIENT, return_value=client):
            finish_run("some-uuid", stats)

        client.table.assert_called_once_with("runs")
        update_call = client.table.return_value.update.call_args[0][0]
        assert update_call["fetched"] == 5
        assert update_call["delivered"] == 2
        assert update_call["duration_seconds"] == 9.9
        client.table.return_value.update.return_value.eq.assert_called_once_with("id", "some-uuid")

    def test_does_not_raise_on_supabase_error(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("db error")

        with patch(PATCH_CLIENT, return_value=client):
            finish_run("some-uuid", RunStats())  # must not raise


class TestFetchRecentRuns:
    def test_returns_data_from_supabase(self):
        rows = [{"id": 1, "fetched": 10}, {"id": 2, "fetched": 7}]
        client = MagicMock()
        (client.table.return_value
               .select.return_value
               .order.return_value
               .limit.return_value
               .execute.return_value) = MagicMock(data=rows)

        with patch(PATCH_CLIENT, return_value=client):
            result = fetch_recent_runs(limit=2)

        assert result == rows
        client.table.return_value.select.assert_called_once_with("*")
        client.table.return_value.select.return_value.order.assert_called_once_with(
            "timestamp", desc=True
        )
        client.table.return_value.select.return_value.order.return_value.limit.assert_called_once_with(2)

    def test_returns_empty_list_on_error(self):
        client = MagicMock()
        (client.table.return_value
               .select.return_value
               .order.return_value
               .limit.return_value
               .execute.side_effect) = Exception("connection error")

        with patch(PATCH_CLIENT, return_value=client):
            result = fetch_recent_runs()

        assert result == []

    def test_default_limit_is_14(self):
        client = MagicMock()
        (client.table.return_value
               .select.return_value
               .order.return_value
               .limit.return_value
               .execute.return_value) = MagicMock(data=[])

        with patch(PATCH_CLIENT, return_value=client):
            fetch_recent_runs()

        client.table.return_value.select.return_value.order.return_value.limit.assert_called_once_with(14)
