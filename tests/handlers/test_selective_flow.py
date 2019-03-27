"""Tests for SelectiveFlowScheduling class."""

import pytest

from f8a_jobs.handlers.selective_flow import SelectiveFlowScheduling


class TestSelectiveFlowScheduling(object):
    """Tests for SelectiveFlowScheduling class."""

    def test_constructor(self):
        """Test the SelectiveFlowScheduling constructor."""
        with pytest.raises(Exception) as e:
            job_id = 1
            SelectiveFlowScheduling(job_id)
            assert e is not None
