"""Tests for NugetPopularAnalyses class."""

import pytest

from f8a_jobs.handlers.nuget_popular_analyses import NugetPopularAnalyses


class TestNugetPopularAnalyses(object):
    """Tests for NugetPopularAnalyses class."""

    def test_constructor(self):
        """Test the NugetPopularAnalyses() constructor."""
        with pytest.raises(Exception) as e:
            job_id = 1
            NugetPopularAnalyses(job_id)
            assert e is not None
