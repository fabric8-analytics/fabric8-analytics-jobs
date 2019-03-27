"""Tests for SelectiveFlowScheduling class."""

from f8a_jobs.handlers.selective_flow import SelectiveFlowScheduling


class TestSelectiveFlowScheduling(object):
    """Tests for SelectiveFlowScheduling class."""

    def test_constructor(self):
        """Test the SelectiveFlowScheduling constructor."""
        assert SelectiveFlowScheduling() is not None
