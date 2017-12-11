import json
from f8a_jobs.handlers import aggregate_crowd_source_tags as acs


def test_single_pkg():
    with open("data/single_pkg.json") as rd:
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


def test_multiple_user_tags():
    with open("data/multiple_user.json") as rd:
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


def test_double_pkg():
    with open("data/double_pkg.json") as rd:
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
