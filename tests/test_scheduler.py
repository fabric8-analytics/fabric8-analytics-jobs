"""Tests for the module 'api_v1'."""

import pytest

from f8a_jobs.scheduler import Scheduler, ScheduleJobError
import f8a_jobs.handlers as handlers


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

    def test_schedule_job_method_state(self):
        """Basic test for the schedule_job method: check state."""
        with pytest.raises(ValueError):
            Scheduler.schedule_job(None, "handler", state="strange_state")

    def test_schedule_job_method_handler_name(self):
        """Basic test for the schedule_job method: check handler name."""
        with pytest.raises(ValueError):
            Scheduler.schedule_job(None, "unknown handler", state=None)

    def test_schedule_job_method_when_parsing(self):
        """Basic test for the schedule_job method: parsing the 'when' parameter."""
        with pytest.raises(ScheduleJobError):
            Scheduler.schedule_job(None, handlers.ErrorHandler, when="xyzzy")

    def test_schedule_job_method_missfirre_grace_time_parsing(self):
        """Basic test for the schedule_job method: parsing the 'missfire_grace_time' parameter."""
        with pytest.raises(ScheduleJobError):
            Scheduler.schedule_job(None, handlers.ErrorHandler,
                                   missfire_grace_time="foo bar baz")

    def test_schedule_job_method_periodically_parsing(self):
        """Basic test for the schedule_job method: parsing the 'periodically' parameter."""
        with pytest.raises(ScheduleJobError):
            Scheduler.schedule_job(None, handlers.ErrorHandler,
                                   periodically="foo bar baz")
