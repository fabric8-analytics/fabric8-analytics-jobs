"""Tests for MavenPopularAnalyses class."""

import pytest

from f8a_jobs.handlers.maven_popular_analyses import MavenPopularAnalyses


class TestMavenPopularAnalyses(object):
    """Tests for MavenPopularAnalyses class."""

    def test_constructor(self):
        """Test the MavenPopularAnalyses() constructor."""
        with pytest.raises(Exception) as e:
            job_id = 1
            MavenPopularAnalyses(job_id)
            assert e is not None
