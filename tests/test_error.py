"""Tests for the module 'error'."""

# import pytest

# TODO enable when new test(s) will be added
from f8a_jobs.error import TokenExpired


class TestError(object):
    """Tests for the module 'error'."""

    def setup_method(self, method):
        """Set up any state tied to the execution of the given method in a class."""
        assert method

    def teardown_method(self, method):
        """Teardown any state that was previously setup with a setup_method call."""
        assert method

    def token_expired(self):
        """Check the error/exception message."""
        e = TokenExpired("Message")
        assert e is not None
        assert str(e) == "Message"
