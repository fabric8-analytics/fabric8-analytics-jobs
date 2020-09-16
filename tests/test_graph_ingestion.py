"""Tests for the module 'graph_ingestion'."""

from unittest import mock
from f8a_jobs.graph_ingestion import \
    ingest_epv_into_graph, \
    run_server_flow, \
    ingest_epv

data_v1 = {
            'body': {
                "npm": [{
                    "package": "pkg1",
                    "version": "ver1"
                }],
                "maven": [{
                    "package": "pkg1",
                    "version": "ver1"
                }]
            }
        }

data_v2 = {
            'body': {
                "npm": [{
                    "package": "pkg1",
                    "version": "ver1"
                }],
                "maven": [{
                    "pkg": "pkg1",
                    "ver": "ver1"
                }]
            }
        }

data_v3 = {
            'body': {
                "npm": [{
                    "package": "pkg1",
                    "version": "ver1"
                }],
                "maven": [{
                    "package": "pkg1",
                    "version": "ver1"
                }, {
                    "pkg": "pkg2",
                    "ver": "ver2"
                }]
            }
        }

data_v4 = {
            'body': {
                "npm": [{
                    "package": "pkg1",
                    "version": "ver1"
                }],
                "nuget": [{
                    "package": "pkg1",
                    "version": "ver1"
                }]
            }
        }


data_v5 = {'nuget': []}


class Dispacher:
    """Dispatcher class returned by Selinon.run_flow."""

    id = "dummy_dispacher_id"


@mock.patch('f8a_jobs.graph_ingestion.run_server_flow', return_value=Dispacher())
def test_ingest_epv_into_graph(_mock):
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_epv_into_graph(data_v1)
    expected = ({
                    'maven': [
                        {
                            'dispacher_id': 'dummy_dispacher_id',
                            'package': 'pkg1',
                            'version': 'ver1'
                        }],
                    'npm': [
                        {
                            'dispacher_id': 'dummy_dispacher_id',
                            'package': 'pkg1',
                            'version': 'ver1'}
                    ]}, 201)
    assert result == expected


@mock.patch('f8a_jobs.graph_ingestion.run_server_flow', return_value=Dispacher())
def test_ingest_epv_into_graph1(_mock):
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_epv_into_graph(data_v2)
    expected = ({
                    'maven': [
                        {
                            'error_message': 'Incorrect data.',
                            'pkg': 'pkg1',
                            'ver': 'ver1'
                        }],
                    'npm': [
                        {
                            'dispacher_id': 'dummy_dispacher_id',
                            'package': 'pkg1',
                            'version': 'ver1'
                        }]}, 201)
    assert result == expected


@mock.patch('f8a_jobs.graph_ingestion.run_server_flow', return_value=Dispacher())
def test_ingest_epv_into_graph2(_mock):
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_epv_into_graph(data_v3)
    expected = ({
                    'maven': [
                        {
                            'dispacher_id': 'dummy_dispacher_id',
                            'package': 'pkg1',
                            'version': 'ver1'
                        }, {
                            'error_message': 'Incorrect data.',
                            'pkg': 'pkg2',
                            'ver': 'ver2'
                        }],
                    'npm': [
                        {
                            'dispacher_id': 'dummy_dispacher_id',
                            'package': 'pkg1',
                            'version': 'ver1'
                        }]}, 201)
    assert result == expected


@mock.patch('f8a_jobs.graph_ingestion.run_server_flow', return_value=Dispacher())
def test_ingest_epv_into_graph3(_mock):
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_epv_into_graph(data_v4)
    expected = ({
                    'npm': [{
                        'dispacher_id': 'dummy_dispacher_id',
                        'package': 'pkg1',
                        'version': 'ver1'
                    }],
                    'nuget': [{
                        'error_message': 'Unsupported ecosystem.'
                    }]
                }, 201)
    assert result == expected


def test_ingest_epv_into_graph4():
    """Tests for 'ingest_epv_into_graph'."""
    result = ingest_epv_into_graph(None)
    expected = ({"message": "Failed to initiate worker flow."}, 500)
    assert result == expected


@mock.patch('f8a_jobs.graph_ingestion.run_flow', return_value=Dispacher())
def test_run_server_flow(_mock1):
    """Tests for 'run_server_flow'."""
    result = run_server_flow('flow_name', {})
    assert result.id == 'dummy_dispacher_id'


def test_ingest_epv():
    """Tests for 'ingest_epv'."""
    result = ingest_epv(body=data_v5)
    expected = ({
                    "nuget": [
                        {'error_message': 'Unsupported ecosystem.'}
                    ]}, 201)
    assert result == expected
