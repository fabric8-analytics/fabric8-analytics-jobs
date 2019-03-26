"""Tests for PythonPopularAnalyses class."""

from f8a_jobs.handlers.python_popular_analyses import PythonPopularAnalyses


class TestPythonPopularAnalyses(object):
    """Tests for PythonPopularAnalyses class."""

    def test_constructor(self):
        """Test the PythonPopularAnalyses() constructor."""
        assert PythonPopularAnalyses(1) is not None
