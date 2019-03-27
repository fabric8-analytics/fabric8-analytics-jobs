"""Tests for SyncToGraph class."""

import pytest

from f8a_jobs.handlers.sync_to_graph import SyncToGraph


class TestSyncToGraph(object):
    """Tests for SyncToGraph class."""

    def test_constructor(self):
        """Test the SyncToGraph() constructor."""
        with pytest.raises(Exception) as e:
            job_id = 1
            SyncToGraph(job_id)
            assert e is not None
