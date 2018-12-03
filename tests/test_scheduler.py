"""Tests for the module 'api_v1'."""

from f8a_jobs.scheduler import ScheduleJobError


class TestScheduler(object):
    """Tests for the module 'scheduler'."""

    def setup_method(self, method):
        """Set up any state tied to the execution of the given method in a class."""
        assert method

    def teardown_method(self, method):
        """Teardown any state that was previously setup with a setup_method call."""
        assert method

    def test_schedule_job_error_class(self):
        """Basic test for the ScheduleJobError class."""
        # well nothing special to do for the empty class derived from Exception
        with pytest.raises(ScheduleJobError):
            raise ScheduleJobError()
