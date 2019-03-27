"""Tests for SyncToGraph class."""

from f8a_jobs.handlers.sync_to_graph import SyncToGraph


class TestSyncToGraph(object):
    """Tests for SyncToGraph class."""

    def test_constructor(self):
        """Test the SyncToGraph() constructor."""
        assert SyncToGraph() is not None
