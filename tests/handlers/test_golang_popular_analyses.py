"""Tests for GolangPopularAnalyses class."""

from f8a_jobs.handlers.golang_popular_analyses import GolangPopularAnalyses


class TestGolangPopularAnalyses(object):
    """Tests for GolangPopularAnalyses class."""

    def test_constructor(self):
        """Test the GolangPopularAnalyses() constructor."""
        assert GolangPopularAnalyses(1) is not None
