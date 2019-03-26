"""Tests for NpmPopularAnalyses class."""

import pytest

from f8a_jobs.handlers.npm_popular_analyses import NpmPopularAnalyses


class TestNpmPopularAnalyses(object):
    """Tests for NpmPopularAnalyses class."""

    def test_constructor(self):
        """Test the NpmPopularAnalyses() constructor."""
        with pytest.raises(Exception) as e:
            job_id = 1
            NpmPopularAnalyses(job_id)
            assert e is not None
