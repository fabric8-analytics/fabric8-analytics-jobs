"""Tests for base.py."""

import pytest
from f8a_jobs.handlers.base import AnalysesBaseHandler


class TestAnalysesBaseHandler(object):
    """Tests for AnalysesBaseHandler class."""

    @pytest.mark.parametrize(('count', 'expected'), [
        ('10', (1, 10)),
        ('2-10', (2, 10))
    ])
    def test_parse_count(self, count, expected):
        """Test parse_count()."""
        assert AnalysesBaseHandler.parse_count(count) == expected
