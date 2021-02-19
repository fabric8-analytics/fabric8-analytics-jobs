"""Module that contains functions for EPV ingestion in Graph DB."""

from selinon import run_flow, run_flow_selective
import logging
import os
from f8a_jobs.utils import requires_auth
from f8a_utils.gh_utils import GithubUtils
from f8a_utils.tree_generator import GolangDependencyTreeGenerator

logger = logging.getLogger(__name__)

_INVOKE_API_WORKERS = os.environ.get('INVOKE_API_WORKERS', 'True') == 'True'
_DISABLE_UNKNOWN_PACKAGE_FLOW = os.environ.get('DISABLE_UNKNOWN_PACKAGE_FLOW', 'False') == 'True'
_SUPPORTED_ECOSYSTEMS = {'npm', 'maven', 'pypi', 'golang'}


def ingest_epv_into_graph(epv_details):
    """Handle implementation of API for triggering ingestion flow.

    :param epv_details: A dictionary object having list of packages/version as a nested object.
    Ex:
    {
          "ecosystem": "<ecosystem_name>",     (*required)
          "packages": [
            {
              "package": "<package_name_1>",   (*required)
              "version": "<package_version_1>" (*required)
            }, {
              "package": "<package_name_2>",   (*required)
              "version": "<package_version_2>" (*required)
            }
          ],
          "force": false,              (optional)
          "force_graph_sync": true,    (optional)
          "recursive_limit": 0         (optional)
          "source": "<Consumer_of_API>"(optional)
        }
    """
    logger.info('graph_ingestion_:_ingest_epv_into_graph() is called.')
    input_data = epv_details.get('body', {})

    # Check if worker flow activation is disabled.
    if not _INVOKE_API_WORKERS:
        logger.debug('Worker flows are disabled.')
        input_data['message'] = 'Worker flows are disabled.'
        return input_data, 201

    # Check if API consumer is CA or SA and unknown package ingestion flag is disabled.
    if _DISABLE_UNKNOWN_PACKAGE_FLOW and input_data.get('source', '') == 'api':
        logger.debug('Unknown package ingestion is disabled.')
        input_data['message'] = 'Unknown package ingestion is disabled.'
        return input_data, 201

    gh = GithubUtils()
    ecosystem = input_data.get('ecosystem')
    package_list = input_data.get('packages')

    node_arguments = {
        "ecosystem": ecosystem,
        "force": input_data.get('force', True),
        "recursive_limit": input_data.get('recursive_limit', 0),
        "force_graph_sync": input_data.get('force_graph_sync', False)
    }

    # Iterate through packages given for current ecosystem.
    for item in package_list:
        if ecosystem == 'golang':
            _, clean_version = GolangDependencyTreeGenerator.\
                clean_version(item.get('version'))
            if gh.is_pseudo_version(clean_version):
                item['error_message'] = 'Golang pseudo version is not supported.'
                continue

        flow_name = 'newPackageFlow' if ecosystem == 'golang' else 'bayesianApiFlow'

        if 'flow_name' in input_data:
            flow_name = input_data['flow_name']

        node_arguments['name'] = item.get('package')
        node_arguments['version'] = item.get('version')

        try:
            # Initiate Selinon flow for current EPV ingestion.
            dispacher_id = run_flow(flow_name, node_arguments)
            item['dispacher_id'] = dispacher_id.id
        except Exception as e:
            logger.error('Exception while initiating the worker flow %s', e)
            return {'message': 'Failed to initiate worker flow.'}, 500

        logger.info('A %s in initiated for eco: %s, pkg: %s, ver: %s',
                    flow_name, ecosystem, item['package'], item['version'])

    return input_data, 201


def ingest_selective_epv_into_graph(epv_details):
    """Handle implementation of API for triggering selective ingestion for any flow.

    :param epv_details: A dictionary having list of packages/version/tasks as a nested object.
    Ex:
    {
          "ecosystem": "<ecosystem_name>",     (*required)
          "packages": [
            {
              "package": "<package_name_1>",   (*required)
              "version": "<package_version_1>" (*required)
            }, {
              "package": "<package_name_2>",   (*required)
              "version": "<package_version_2>" (optional)
            }
          ],
          "task_names": [                      (*required)
            "TASK_1",
            "TASK_2",
            "TASK_3",
            "TASK_4"
          ],
          "force": false,              (optional)
          "recursive_limit": 0         (optional)
          "follow_subflows": true,     (optional)
          "run_subsequent": false,     (optional)
          "source": "<Consumer_of_API>"(optional)
        }
    """
    logger.info('graph_ingestion_:_ingest_selective_epv_into_graph is called.')
    input_data = epv_details.get('body', {})

    # Check if worker flow activation is disabled.
    if not _INVOKE_API_WORKERS:
        logger.debug('Worker flows are disabled.')
        input_data['message'] = 'Worker flows are disabled.'
        return input_data, 201

    ecosystem = input_data.get('ecosystem')
    package_list = input_data.get('packages')
    task_names = input_data.get('task_names')
    follow_subflows = input_data.get('follow_subflows', False)
    run_subsequent = input_data.get('run_subsequent', False)

    if input_data.get('source', '') == 'git-refresh':
        flow_name = 'newPackageAnalysisFlow' \
            if ecosystem == 'golang' else 'bayesianPackageFlow'

    if 'flow_name' in input_data:
        flow_name = input_data['flow_name']

    node_arguments = {
        "ecosystem": ecosystem,
        "force": input_data.get('force', True)
    }

    # Iterate through packages given for current ecosystem.
    for item in package_list:
        node_arguments["name"] = item.get('package')

        if 'url' in item:
            node_arguments['url'] = item['url']
        if 'version' in item:
            node_arguments['version'] = item['version']

        try:
            # Initiate Selinon flow for current EPV ingestion.
            dispacher_id = run_flow_selective(flow_name,
                                              task_names,
                                              node_arguments,
                                              follow_subflows,
                                              run_subsequent)
            item['dispacher_id'] = dispacher_id.id
        except Exception as e:
            logger.error('Exception while initiating the worker flow %s', e)
            return {'message': 'Failed to initiate worker flow.'}, 500

        logger.info('A selective flow "%s" in initiated for '
                    'eco: %s, pkg: %s, for task list: %s',
                    flow_name, ecosystem, item['package'], task_names)
    return input_data, 201


@requires_auth
def ingest_epv(**kwargs):
    """To handle POST requests for end point '/ingestions/epv'."""
    return ingest_epv_into_graph(kwargs)


@requires_auth
def ingest_selective_epv(**kwargs):
    """To handle POST requests for end point '/ingestions/epv-selective'."""
    return ingest_selective_epv_into_graph(kwargs)


def ingest_epv_internal(**kwargs):
    """To handle POST requests for end point '/internal/ingestions/epv'."""
    return ingest_epv_into_graph(kwargs)


def ingest_selective_epv_internal(**kwargs):
    """To handle POST requests for end point '/internal/ingestions/epv-selective'."""
    return ingest_selective_epv_into_graph(kwargs)
