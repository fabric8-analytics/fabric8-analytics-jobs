"""Tests for AggregateCrowdSourceTags class."""

import json
import os.path
from f8a_jobs.handlers.aggregate_crowd_source_tags import AggregateCrowdSourceTags as ACST


class TestCrowdSourceTags(object):
    """Tests for AggregateCrowdSourceTags class."""

    def test_filter_user_tags_single_pkg(self):
        """Test for filter_user_tags()."""
        data = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', 'single_pkg.json')
        with open(data) as rd:
            correct_data = json.load(rd)
            assert correct_data is not None

        pkg_data = correct_data.get("result", {}).get("data", [])

        user_tag_data = pkg_data[0]
        user_tags = user_tag_data.get("user_tags", [])
        # "user_tags": ["database;scm", "git;scm;version-control;database"]
        pkg_tags, _ = ACST.filter_user_tags(user_tags)
        assert set(pkg_tags) == {'database', 'scm'}

    def test_filter_user_tags_multiple_user_tags(self):
        """Test for filter_user_tags()."""
        data = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', 'multiple_user.json')
        with open(data) as rd:
            correct_data = json.load(rd)
            assert correct_data is not None

        pkg_data = correct_data.get("result", {}).get("data", [])

        user_tag_data = pkg_data[0]
        user_tags = user_tag_data.get("user_tags", [])
        # "user_tags": ["database;scm", "git;scm;version-control;database", "database"]
        pkg_tags, _ = ACST.filter_user_tags(user_tags)
        assert set(pkg_tags) == {'database'}

    def test_filter_user_tags_double_pkg(self):
        """Test for filter_user_tags()."""
        data = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', 'double_pkg.json')
        with open(data) as rd:
            correct_data = json.load(rd)
            assert correct_data is not None

        pkg_data = correct_data.get("result", {}).get("data", [])

        for i, user_tag_data in enumerate(pkg_data):
            user_tags = user_tag_data.get("user_tags", [])
            pkg_tags, _ = ACST.filter_user_tags(user_tags)
            if i == 0:
                # "user_tags": ["database;scm", "git;scm;version-control;database"]
                assert set(pkg_tags) == {'database', 'scm'}
            else:
                # "user_tags": ["service-discovery;client;configuration", "vert.x;client;java"]
                assert set(pkg_tags) == {'client'}
