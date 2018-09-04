#!/usr/bin/env python3

"""Handler for storing information about failed jobs."""

from f8a_jobs.handlers.base import BaseHandler


class ErrorHandler(BaseHandler):
    """Handler for storing information about failed jobs."""

    def execute(self, _exc_str, _exc_traceback, _failed_job_handler, **_failed_handler_kwargs):
        """Do nothing."""
        # Does nothing...as described above
        self.log.info("Error handler executed without effect")
        return
