"""Tests for NpmPopularAnalyses class."""

from f8a_jobs.handlers.npm_popular_analyses import NpmPopularAnalyses


class TestNpmPopularAnalyses(object):
    """Tests for NpmPopularAnalyses class."""

    def test_constructor(self):
        """Test the NpmPopularAnalyses() constructor."""
        assert NpmPopularAnalyses() is not None
