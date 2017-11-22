#!/usr/bin/env python3

from f8a_jobs.handlers.base import BaseHandler


class ErrorHandler(BaseHandler):
    """Handler for storing information about failed jobs."""

    def execute(self, exc_str, exc_traceback, failed_job_handler, **failed_handler_kwargs):
        # Does nothing...
        self.log.info("Error handler executed without effect")
        return
