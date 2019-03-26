"""Tests for MavenPopularAnalyses class."""

from f8a_jobs.handlers.maven_popular_analyses import MavenPopularAnalyses


class TestMavenPopularAnalyses(object):
    """Tests for MavenPopularAnalyses class."""

    def test_constructor(self):
        """Test the MavenPopularAnalyses() constructor."""
        assert MavenPopularAnalyses(1) is not None
