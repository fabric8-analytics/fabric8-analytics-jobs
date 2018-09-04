"""Tests for the module 'utils'."""

import pytest

from f8a_jobs.utils import parse_dates


class TestUtilFunctions(object):
    """Tests for the module 'utils'."""

    def setup_method(self, method):
        """Set up any state tied to the execution of the given method in a class."""
        assert method

    def teardown_method(self, method):
        """Teardown any state that was previously setup with a setup_method call."""
        assert method

    def test_parse_dates(self):
        """Test for the function parse_dates."""
        from_date = '2017-01-01'
        to_date = '2018-01-01'
        job_kwargs = {'from_date': from_date,
                      'to_date': to_date}
        # should just pass, no need to check result
        parse_dates(job_kwargs)

        from_date = '2017-01-41'
        job_kwargs = {'from_date': from_date,
                      'to_date': to_date}
        with pytest.raises(ValueError):
            parse_dates(job_kwargs)
