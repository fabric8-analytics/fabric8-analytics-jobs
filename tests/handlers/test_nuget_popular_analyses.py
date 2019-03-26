"""Tests for NugetPopularAnalyses class."""

from f8a_jobs.handlers.nuget_popular_analyses import NugetPopularAnalyses


class TestNugetPopularAnalyses(object):
    """Tests for NugetPopularAnalyses class."""

    def test_constructor(self):
        """Test the NugetPopularAnalyses() constructor."""
        assert NugetPopularAnalyses() is not None
