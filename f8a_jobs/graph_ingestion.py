"""Module that contains functions for EPV ingestion in Graph DB."""

from selinon import run_flow
import logging
import flask
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
    'eco1': [{"package": "p1", "version": "v1"},{"package": "p2", "version": "v2"}],
    'eco2': [{"package": "p1", "version": "v1"},{"package": "p2", "version": "v2"}]
    }
    """
    response = {}

    try:
        logger.info('graph_ingestion_:_ingest_epv_into_graph() is called.')
        input_data = epv_details.get('body', {})

        # Check if EPV ingestion is enabled.
        if _INVOKE_API_WORKERS:

            # Iterate through ecosystem present in input data
            for eco, items in input_data.items():

                # Check if requested ecosystem for ingestion is supported,
                # if not then set an error message.
                if eco in _SUPPORTED_ECOSYSTEMS:
                    dispacher_ids = []
                    incorrect_epv = []
                    response[eco] = {
                        'dispacher_ids': dispacher_ids,
                    }

                    # Iterate through packages given for current ecosystem.
                    for item in items:
                        # Check if required keys are present in input data,
                        # if not then add item in filed list.
                        if {'package', 'version'}.issubset(item.keys()):
                            node_arguments = {
                                "ecosystem": eco,
                                "force": True,
                                "force_graph_sync": False,
                                "name": item['package'],
                                "recursive_limit": 0,
                                "version": item['version']
                            }

                            # Initiate Selinon flow for current EPV ingestion.
                            dispacher_id = run_server_flow(_FLOW_NAME, node_arguments)
                            dispacher_ids.append(dispacher_id.id)

                            logger.info('A {} in initiated for eco: {}, pkg: {}, ver: {}'
                                        .format(_FLOW_NAME, eco, item['package'], item['version']))
                        else:
                            logger.error('Incorrect data sent for {}: {}'.format(eco, item))
                            incorrect_epv.append(item)

                    # Check if any of the epv had incorrect data,
                    # if yes then send list of them in response.
                    if incorrect_epv:
                        response[eco]['incorrect_epv'] = incorrect_epv
                else:
                    response[eco] = 'Unsupported ecosystem'

            return flask.jsonify(response), 201
    except Exception as e:
        logger.error('Exception while initiating the worker flow {}'.format(e))
        return flask.jsonify({'message': 'Failed to initiate worker flow.'}), 500


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
