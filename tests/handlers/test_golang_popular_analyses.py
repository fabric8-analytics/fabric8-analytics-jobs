"""Tests for GolangPopularAnalyses class."""

import pytest

from f8a_jobs.handlers.golang_popular_analyses import GolangPopularAnalyses


class TestGolangPopularAnalyses(object):
    """Tests for GolangPopularAnalyses class."""

    def test_constructor(self):
        """Test the GolangPopularAnalyses() constructor."""
        with pytest.raises(Exception) as e:
            job_id = 1
            GolangPopularAnalyses(job_id)
            assert e is not None
