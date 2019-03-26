"""Tests for book_keeping.py."""

import pytest

# TODO enable when new test(s) will be added
# from f8a_jobs.handlers.book_keeping import BookKeeping


class TestBookKeeping(object):
    """Tests for BookKeeping class."""

    def setup_method(self, method):
        """Set up any state tied to the execution of the given method in a class."""
        assert method

    def teardown_method(self, method):
        """Teardown any state that was previously setup with a setup_method call."""
        assert method
