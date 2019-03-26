"""Tests for PythonPopularAnalyses class."""

import pytest

from f8a_jobs.handlers.python_popular_analyses import PythonPopularAnalyses


class TestPythonPopularAnalyses(object):
    """Tests for PythonPopularAnalyses class."""

    def test_constructor(self):
        """Test the PythonPopularAnalyses() constructor."""
        with pytest.raises(Exception) as e:
            job_id = 1
            PythonPopularAnalyses(job_id)
            assert e is not None
