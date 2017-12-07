import pytest

from f8a_jobs.utils import parse_dates


class TestUtilFunctions(object):
    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    def test_parse_dates(self):
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
