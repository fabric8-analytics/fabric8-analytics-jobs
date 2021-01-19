"""Tests for the module 'graph_ingestion'."""

from unittest import mock
from f8a_jobs.graph_ingestion import (ingest_epv_into_graph,
                                      run_server_flow,
                                      ingest_epv,
                                      ingest_selective_epv_into_graph,
                                      ingest_selective_epv,
                                      ingest_epv_internal,
                                      ingest_selective_epv_internal)

data_v1 = {
            'body': {
                "ecosystem": "npm",
                "packages": [{
                    "package": "pkg1",
                    "version": "ver1"
                }
                ],
                "force": False,
                "force_graph_sync": True,
                "recursive_limit": 0
            }
        }


data_v2 = {
            'body': {
                "ecosystem": "npm",
                "packages": [{
                    "pkg": "pkg1",
                    "ver": "ver1"
                }],
                "force": False,
                "force_graph_sync": True,
                "recursive_limit": 0
            }
        }

data_v3 = {
            'body': {
                "ecosystem": "nuget",
                "packages": [{
                    "package": "pkg1",
                    "version": "ver1"
                }
                ],
                "force": False,
                "force_graph_sync": True,
                "recursive_limit": 0
            }
        }

data_v4 = {
            'body': {
                "ecosystem": "golang",
                "packages": [{
                    "package": "pkg1"
                }
                ],
                "flow_name": "flow_name",
                "task_names": [
                    "TASK_1",
                    "TASK_2",
                    "TASK_3",
                    "TASK_4"
                ]
            }
        }

data_v5 = {
            'body': {
                "ecosystem": "npm",
                "packages": [{
                    "package": "pkg1",
                    "version": "ver1"
                }
                ],
                "force": False,
                "force_graph_sync": True,
                "recursive_limit": 0,
                "flow_name": 'flow_name'
            }
        }

data_v6 = {
            'body': {
                "ecosystem": "golang",
                "packages": [{
                    "package": "pkg1",
                    "url": "https://github.com/",
                    "version": "ver1"
                }
                ],
                "flow_name": "flow_name",
                "task_names": [
                    "TASK_1",
                    "TASK_2",
                    "TASK_3",
                    "TASK_4"
                ]
            }
        }

data_v7 = {
            "ecosystem": "nuget",
            "packages": [{
                "package": "pkg1"
            }
            ],
            "source": "git-refresh",
            "task_names": [
                "TASK_1",
                "TASK_2",
                "TASK_3",
                "TASK_4"
            ]
        }

data_v8 = {
            'body': {
                "ecosystem": "golang",
                "packages": [{
                    "package": "pkg1",
                    "version": "ver1"
                }
                ]
            }
        }

data_v9 = {
            'body': {
                "ecosystem": "npm",
                "packages": [{
                    "package": "pkg1",
                    "version": "ver1"
                }
                ],
                "source": "api"
            }
        }

data_v10 = {
            'body': {
                "ecosystem": "npm",
                "packages": [{
                    "package": "pkg1",
                    "version": "ver1"
                }
                ],
                "flow_name": None
            }
        }


class Dispacher:
    """Dispatcher class returned by Selinon.run_flow."""

    id = "dummy_dispacher_id"


@mock.patch('f8a_jobs.graph_ingestion.run_server_flow', return_value=Dispacher())
def test_ingest_epv_into_graph(_mock):
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_epv_into_graph(data_v1)
    expected = ({
                    'ecosystem': 'npm',
                    'force': False,
                    'force_graph_sync': True,
                    'packages': [{
                        'dispacher_id': 'dummy_dispacher_id',
                        'package': 'pkg1',
                        'version': 'ver1'}],
                    'recursive_limit': 0
                }, 201)
    assert result == expected


@mock.patch('f8a_jobs.graph_ingestion.run_server_flow', return_value=Dispacher())
def test_ingest_epv_into_graph1(_mock):
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_epv_into_graph(data_v2)
    expected = ({
                     'ecosystem': 'npm',
                     'force': False,
                     'force_graph_sync': True,
                     'packages': [{
                         'error_message': 'Incorrect data.',
                         'pkg': 'pkg1',
                         'ver': 'ver1'}],
                     'recursive_limit': 0}, 201)
    assert result == expected


def test_ingest_epv_into_graph4():
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_epv_into_graph(data_v10)
    expected = ({"message": "Failed to initiate worker flow."}, 500)
    assert result == expected


@mock.patch('f8a_jobs.graph_ingestion.run_flow', return_value=Dispacher())
def test_run_server_flow(_mock1):
    """Tests for 'run_server_flow'."""
    result = run_server_flow('flow_name', {})
    assert result.id == 'dummy_dispacher_id'


def test_ingest_epv():
    """Tests for 'ingest_epv'."""
    result = ingest_epv(body=data_v3)
    expected = ({
                    'body': {
                        'ecosystem': 'nuget',
                        'force': False,
                        'force_graph_sync': True,
                        'packages': [{
                            'package': 'pkg1',
                            'version': 'ver1'
                        }],
                        'recursive_limit': 0},
                    'error_message': 'Unsupported ecosystem.'
                }, 201)

    assert result == expected


@mock.patch('f8a_jobs.graph_ingestion.run_server_flow', return_value=Dispacher())
def test_ingest_epv_into_graph5(_mock):
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_epv_into_graph(data_v5)
    expected = ({
                    'ecosystem': 'npm',
                    'force': False,
                    'force_graph_sync': True,
                    'packages': [{
                        'dispacher_id': 'dummy_dispacher_id',
                        'package': 'pkg1',
                        'version': 'ver1'}],
                    'recursive_limit': 0,
                    'flow_name': 'flow_name'
                }, 201)
    assert result == expected


@mock.patch('f8a_jobs.graph_ingestion.run_flow_selective', return_value=Dispacher())
def test_ingest_selective_epv_into_graph(_mock):
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_selective_epv_into_graph(data_v4)
    expected = ({
                    'ecosystem': 'golang',
                    'flow_name': 'flow_name',
                    'packages': [{
                        'dispacher_id': 'dummy_dispacher_id',
                        'package': 'pkg1'}]
                }, 201)
    assert result == expected


@mock.patch('f8a_jobs.graph_ingestion.run_flow_selective', return_value=Dispacher())
def test_ingest_selective_epv_into_graph2(_mock):
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_selective_epv_into_graph(data_v6)
    expected = ({
                    'ecosystem': 'golang',
                    'flow_name': 'flow_name',
                    'packages': [{
                        'dispacher_id': 'dummy_dispacher_id',
                        'package': 'pkg1',
                        "url": "https://github.com/",
                        "version": "ver1"
                    }]
                }, 201)
    assert result == expected


def test_ingest_selective_epv():
    """Tests for 'ingest_epv'."""
    result = ingest_selective_epv(body=data_v7)
    expected = ({
                    'message': 'Failed to initiate worker flow.'
                }, 500)

    assert result == expected


@mock.patch('f8a_jobs.graph_ingestion.GithubUtils.is_pseudo_version', return_value=True)
def test_ingest_epv_into_graph6(_mock):
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_epv_into_graph(data_v8)

    expected = ({'ecosystem': 'golang',
                 'packages': [{
                     'error_message': 'Golang pseudo version is not supported.',
                     'package': 'pkg1',
                     'version': 'ver1'}]},
                201)
    assert result == expected


def test_ingest_epv_internal():
    """Tests for 'ingest_epv_internal'."""
    result = ingest_epv_internal(body=data_v3)
    expected = ({
                    'body': {
                        'ecosystem': 'nuget',
                        'force': False,
                        'force_graph_sync': True,
                        'packages': [{
                            'package': 'pkg1',
                            'version': 'ver1'
                        }],
                        'recursive_limit': 0},
                    'error_message': 'Unsupported ecosystem.'
                }, 201)

    assert result == expected


def test_ingest_selective_epv_internal():
    """Tests for 'ingest_epv_internal'."""
    result = ingest_selective_epv_internal(body=data_v7)
    expected = ({
                    'message': 'Failed to initiate worker flow.'
                }, 500)

    assert result == expected


@mock.patch('f8a_jobs.graph_ingestion.run_server_flow', return_value=Dispacher())
@mock.patch("f8a_jobs.graph_ingestion._DISABLE_UNKNOWN_PACKAGE_FLOW", return_value=True)
def test_ingest_epv_into_graph7(_mock1, _mock2):
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_epv_into_graph(data_v9)
    expected = ({'ecosystem': 'npm',
                 'message': 'Unknown package ingestion is disabled.',
                 'packages': [{
                     'package': 'pkg1',
                     'version': 'ver1'}],
                 'source': 'api'},
                201)
    assert result == expected
