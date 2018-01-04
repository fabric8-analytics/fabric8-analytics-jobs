import json
import os.path
from f8a_jobs.handlers.aggregate_crowd_source_tags import AggregateCrowdSourceTags as ACST


class TestCrowdSourceTag(object):

    def test_single_pkg(self):
        data = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', 'single_pkg.json')
        with open(data) as rd:
            correct_data = json.load(rd)
        pkg_data = correct_data.get("result", {}).get("data", [])
        assert (len(pkg_data) == 1)
        for user_tag_data in pkg_data:
            user_tags = user_tag_data.get("user_tags", [])
            pt = []
            for ut in user_tags:
                utt = ACST.process_tags(ut)
                if not pt:
                    pt = set(utt)
                else:
                    pt = pt & set(utt)
            # "user_tags": ["database;scm", "git;scm;version-control;database"]
            assert (pt == {'database', 'scm'})

    def test_multiple_user_tags(self):
        data = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', 'multiple_user.json')
        with open(data) as rd:
            correct_data = json.load(rd)
        pkg_data = correct_data.get("result", {}).get("data", [])
        assert (len(pkg_data) == 1)
        for user_tag_data in pkg_data:
            user_tags = user_tag_data.get("user_tags", [])
            assert (len(user_tags) == 3)
            pt = []
            for ut in user_tags:
                utt = ACST.process_tags(ut)
                if pt == []:
                    pt = set(utt)
                else:
                    pt = pt & set(utt)
            assert (len(pt) == 1)
            # "user_tags": ["database;scm", "git;scm;version-control;database", "database"],
            assert (pt == {'database'})

    def test_double_pkg(self):
        data = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', 'double_pkg.json')
        with open(data) as rd:
            correct_data = json.load(rd)
        pkg_data = correct_data.get("result", {}).get("data", [])
        assert (len(pkg_data) == 2)
        for i, user_tag_data in enumerate(pkg_data):
            user_tags = user_tag_data.get("user_tags", [])
            pkg_name = user_tag_data.get("name")[0]
            pt = []
            for ut in user_tags:
                utt = ACST.process_tags(ut)
                if pt == []:
                    pt = set(utt)
                else:
                    pt = pt & set(utt)
            if i == 0:
                # "user_tags": ["database;scm", "git;scm;version-control;database"],
                assert (pkg_name == "org.ongit:eclipse.jgit")
                assert (pt == {'database', 'scm'})
            else:
                # "user_tags": ["service-discovery;client;configuration", "vert.x;client;java"],
                assert (pkg_name == "io.vertx:vertx-client")
                assert (pt == {'client'})
