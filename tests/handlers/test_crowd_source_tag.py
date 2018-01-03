import json
import os.path
from f8a_jobs.handlers import aggregate_crowd_source_tags as acs


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
            pkg_name = user_tag_data.get("name")[0]
            assert (len(user_tags) == 2)
            assert (pkg_name == "org.ongit:eclipse.jgit")
            pt = []
            for ut in user_tags:
                utt = acs._process_tags(ut)
                if pt == []:
                    pt = set(utt)
                else:
                    pt = pt & set(utt)
            assert (len(pt) == 2)
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
            pkg_name = user_tag_data.get("name")[0]
            assert (len(user_tags) == 3)
            assert (pkg_name == "org.ongit:eclipse.jgit")
            pt = []
            for ut in user_tags:
                utt = acs._process_tags(ut)
                if pt == []:
                    pt = set(utt)
                else:
                    pt = pt & set(utt)
            assert (len(pt) == 1)
            assert (pt == {'database'})

    def test_double_pkg(self):
        data = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', 'double_pkg.json')
        with open(data) as rd:
            correct_data = json.load(rd)
        pkg_data = correct_data.get("result", {}).get("data", [])
        assert (len(pkg_data) == 2)
        i = 1
        for user_tag_data in pkg_data:
            user_tags = user_tag_data.get("user_tags", [])
            pkg_name = user_tag_data.get("name")[0]
            pt = []
            for ut in user_tags:
                utt = acs._process_tags(ut)
                if pt == []:
                    pt = set(utt)
                else:
                    pt = pt & set(utt)
            if i == 1:
                i = i + 1
                assert (pkg_name == "org.ongit:eclipse.jgit")
                assert (pt == {'database', 'scm'})
            else:
                assert (pkg_name == "io.vertx:vertx-client")
                assert (pt == {'client'})
