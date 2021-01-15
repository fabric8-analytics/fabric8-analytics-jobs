"""Module that contains functions for EPV ingestion in Graph DB."""

from selinon import run_flow, run_flow_selective
import logging
import os
from f8a_jobs.utils import validate_user
from f8a_utils.gh_utils import GithubUtils
from f8a_utils.tree_generator import GolangDependencyTreeGenerator

logger = logging.getLogger(__name__)

_INVOKE_API_WORKERS = True \
    if os.environ.get('INVOKE_API_WORKERS', 'True') == 'True' \
    else False

_DISABLE_UNKNOWN_PACKAGE_FLOW = True \
    if os.environ.get('DISABLE_UNKNOWN_PACKAGE_FLOW', 'False') == 'True' \
    else False

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
        }
    """
    try:
        logger.info('graph_ingestion_:_ingest_epv_into_graph() is called.')
        input_data = epv_details.get('body', {})
        source = input_data.get('source', '')

        if source in ['api'] and _DISABLE_UNKNOWN_PACKAGE_FLOW:
            logger.debug('Unknown package ingestion is disabled.')
            input_data['message'] = 'Unknown package ingestion is disabled.'
            return input_data, 201

        # Check if EPV ingestion is enabled.
        if _INVOKE_API_WORKERS:
            ecosystem = input_data.get('ecosystem')
            force = input_data.get('force', True)
            force_graph_sync = input_data.get('force_graph_sync', False)
            recursive_limit = input_data.get('recursive_limit', 0)

            # Check if requested ecosystem for ingestion is supported,
            # if not then set an error message.
            if ecosystem in _SUPPORTED_ECOSYSTEMS:
                package_list = input_data.get('packages')
                gh = GithubUtils()

                # Iterate through packages given for current ecosystem.
                for item in package_list:
                    # Check if required keys are present in input data,
                    # if not then add item in filed list.
                    if {'package', 'version'}.issubset(item.keys()):
                        if ecosystem == 'golang':
                            _, clean_version = GolangDependencyTreeGenerator.\
                                clean_version(item.get('version'))
                            if gh.is_pseudo_version(clean_version):
                                item['error_message'] = 'Golang pseudo version is not supported.'
                                continue

                        node_arguments = {
                            "ecosystem": ecosystem,
                            "force": force,
                            "force_graph_sync": force_graph_sync,
                            "name": item.get('package'),
                            "recursive_limit": recursive_limit,
                            "version": item.get('version')
                        }

                        flow_name = 'newPackageFlow' \
                            if ecosystem == 'golang' \
                            else 'bayesianApiFlow'

                        if 'flow_name' in input_data:
                            flow_name = input_data['flow_name']

                        # Initiate Selinon flow for current EPV ingestion.
                        dispacher_id = run_server_flow(flow_name, node_arguments)
                        item['dispacher_id'] = dispacher_id.id

                        logger.info('A {} in initiated for eco: {}, pkg: {}, ver: {}'
                                    .format(flow_name,
                                            ecosystem,
                                            item['package'],
                                            item['version']))
                    else:
                        logger.error('Incorrect data sent for {}: {}'.format(ecosystem, item))
                        item['error_message'] = 'Incorrect data.'
            else:
                input_data['error_message'] = 'Unsupported ecosystem.'

            return input_data, 201
    except Exception as e:
        logger.error('Exception while initiating the worker flow {}'.format(e))
        return {'message': 'Failed to initiate worker flow.'}, 500


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
        }
    """
    try:
        logger.info('graph_ingestion_:_ingest_selective_epv_into_graph is called.')
        input_data = epv_details.get('body', {})

        # Check if EPV ingestion is enabled.
        if _INVOKE_API_WORKERS:
            ecosystem = input_data.get('ecosystem')
            package_list = input_data.get('packages')
            flow_name = input_data.get('flow_name')
            task_names = input_data.get('task_names')
            force = input_data.get('force', True)
            follow_subflows = input_data.get('follow_subflows', False)
            run_subsequent = input_data.get('run_subsequent', False)

            input_data.pop('follow_subflows', None)
            input_data.pop('run_subsequent', None)
            input_data.pop('task_names')
            input_data.pop('force', None)

            # Iterate through packages given for current ecosystem.
            for item in package_list:
                node_arguments = {
                    "ecosystem": ecosystem,
                    "force": force,
                    "name": item.get('package'),
                }

                if 'url' in item:
                    node_arguments['url'] = item['url']
                if 'version' in item:
                    node_arguments['version'] = item['version']

                # Initiate Selinon flow for current EPV ingestion.
                dispacher_id = run_flow_selective(flow_name,
                                                  task_names,
                                                  node_arguments,
                                                  follow_subflows,
                                                  run_subsequent)
                item['dispacher_id'] = dispacher_id.id

                logger.info('A selective flow "{}" in initiated for '
                            'eco: {}, pkg: {}, for task list: {}'
                            .format(flow_name,
                                    ecosystem,
                                    item['package'],
                                    task_names))
            return input_data, 201
    except Exception as e:
        logger.error('Exception while initiating the worker flow {}'.format(e))
        return {'message': 'Failed to initiate worker flow.'}, 500


def run_server_flow(flow_name, node_args):
    """To run the worker flow via selinon.

    :param flow_name: Name of the ingestion flow
    :param node_args: Details required by Selinon task manager for triggering a flow.
    :return: Selinon Dispatcher ID associated to flow started.
    """
    return run_flow(flow_name, node_args)


@validate_user
def ingest_epv(**kwargs):
    """To handle POST requests for end point '/ingestions/epv'."""
    return ingest_epv_into_graph(kwargs)


@validate_user
def ingest_selective_epv(**kwargs):
    """To handle POST requests for end point '/ingestions/epv-selective'."""
    return ingest_selective_epv_into_graph(kwargs)


def ingest_epv_internal(**kwargs):
    """To handle POST requests for end point '/internal/ingestions/epv'."""
    return ingest_epv_into_graph(kwargs)


def ingest_selective_epv_internal(**kwargs):
    """To handle POST requests for end point '/internal/ingestions/epv-selective'."""
    return ingest_selective_epv_into_graph(kwargs)
