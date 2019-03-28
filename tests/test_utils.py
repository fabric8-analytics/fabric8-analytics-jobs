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
        job_kwargs = {}
        # should just pass, no need to check result
        parse_dates(job_kwargs)

        from_date = '2017-01-01'
        to_date = '2018-01-01'
        job_kwargs = {'from_date': from_date,
                      'to_date': to_date}
        # should just pass, no need to check result
        parse_dates(job_kwargs)

        # illegal date
        from_date = '2017-01-41'
        job_kwargs = {'from_date': from_date,
                      'to_date': to_date}
        with pytest.raises(ValueError):
            parse_dates(job_kwargs)

        # legal date
        from_date = '2017-01-01'
        # illegal date
        to_date = '2017-01-41'
        job_kwargs = {'from_date': from_date,
                      'to_date': to_date}
        with pytest.raises(ValueError):
            parse_dates(job_kwargs)

    def test_parse_dates_return_value(self):
        """Test for the function parse_dates."""
        job_kwargs = {}
        parse_dates(job_kwargs)
        assert job_kwargs == {}

        from_date = '2017-01-01'
        to_date = '2018-01-01'
        job_kwargs = {'from_date': from_date,
                      'to_date': to_date}
        parse_dates(job_kwargs)

        assert 'from_date' in job_kwargs
        assert 'to_date' in job_kwargs

        assert job_kwargs['from_date'] == '2017-01-01'
        assert job_kwargs['to_date'] == '2018-01-01'
