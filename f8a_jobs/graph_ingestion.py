"""Module that contains functions for EPV ingestion in Graph DB."""

from selinon import run_flow
import logging
import os
from f8a_jobs.utils import validate_user

logger = logging.getLogger(__name__)

_INVOKE_API_WORKERS = True \
    if os.environ.get('INVOKE_API_WORKERS', '1') == '1' \
    else False
_FLOW_NAME = 'bayesianApiFlow' \
    if os.environ.get('WORKER_ADMINISTRATION_REGION', 'api') == 'api' \
    else 'bayesianFlow'
_SUPPORTED_ECOSYSTEMS = {'npm', 'maven', 'pypi'}


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

                # Iterate through packages given for current ecosystem.
                for item in package_list:
                    # Check if required keys are present in input data,
                    # if not then add item in filed list.
                    if {'package', 'version'}.issubset(item.keys()):
                        node_arguments = {
                            "ecosystem": ecosystem,
                            "force": force,
                            "force_graph_sync": force_graph_sync,
                            "name": item.get('package'),
                            "recursive_limit": recursive_limit,
                            "version": item.get('version')
                        }

                        # Initiate Selinon flow for current EPV ingestion.
                        dispacher_id = run_server_flow(_FLOW_NAME, node_arguments)
                        item['dispacher_id'] = dispacher_id.id

                        logger.info('A {} in initiated for eco: {}, pkg: {}, ver: {}'
                                    .format(_FLOW_NAME,
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
