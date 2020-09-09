"""Module that contains functions for EPV ingestion in Graph DB."""

from selinon import run_flow
import logging
import f8a_jobs.defaults as defaults
import flask
from flask import request
import os

logger = logging.getLogger(__name__)

_INVOKE_API_WORKERS = True \
    if os.environ.get('INVOKE_API_WORKERS', '1') == '1' \
    else False
_FLOW_NAME = 'bayesianApiFlow' \
    if os.environ.get('WORKER_ADMINISTRATION_REGION', 'api') == 'api' \
    else 'bayesianFlow'
_SUPPORTED_ECOSYSTEMS = {'npm', 'maven', 'pypi'}


def ingest_epv_into_graph(epv_details):
    """Handle POST requests for triggering ingestion flow.

    :param epv_details: A dictionary object having list of packages/version as a nested object.
    Ex:
    {
    'eco1': [{"package": "p1", "version": "v1"},{"package": "p2", "version": "v2"}],
    'eco2': [{"package": "p1", "version": "v1"},{"package": "p2", "version": "v2"}]
    }
    """
    resp = {}
    dispacher_ids = []

    try:
        logger.info('graph_ingestion_:_ingest_epv_into_graph() is called.')
        input_data = epv_details.get('body', {})

        # Check if EPV ingestion is enabled.
        if _INVOKE_API_WORKERS:
            # Check if requested ecosystem for ingestion is supported.
            if not set(input_data.keys()).issubset(_SUPPORTED_ECOSYSTEMS):
                logger.info('Unsupported ecosystem provided.')
                return flask.jsonify({'message': 'Unsupported ecosystem provided.',
                                      'success': False}), 400

            # Iterate through ecosystem present in input data
            for eco, items in input_data.items():

                # Iterate through packages given for current ecosystem.
                for item in items:
                    # Check if required keys are present in input data
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
                        logger.info('Incorrect data sent for {}: {}'.format(eco, items))
                        message = {'message': 'Incorrect data sent for {}::{}'.format(eco, items),
                                   'success': False}

                        if dispacher_ids:
                            message['dispacher_ids'] = dispacher_ids
                        return flask.jsonify(message), 400

            resp['dispacher_ids'] = dispacher_ids
            resp['message'] = 'All ingestion flows are initiated'
            resp['success'] = True

            return flask.jsonify(resp), 201
    except Exception as e:
        logger.error('Exception while initiating the worker flow {}'.format(e))
        return flask.jsonify({'message': 'Failed to initiate worker flow.', 'success': False}), 500


def run_server_flow(flow_name, node_args):
    """To run the worker flow via selinon.

    :param flow_name: Name of the ingestion flow
    :param node_args: Details required by Selinon task manager for triggering a flow.
    :return: Selinon Dispatcher ID associated to flow started.
    """
    return run_flow(flow_name, node_args)


def ingest_epv(**kwargs):
    """To handle requests for end point '/ingestions/ingest-epv'."""
    # Check if user authentication is disabled,
    # if not then validate the token provided by the user.
    if not defaults.DISABLE_AUTHENTICATION:
        auth_token = request.headers.get('auth_token', '')

        if auth_token != defaults.APP_SECRET_KEY:
            return flask.jsonify({'message': 'Unauthorized!!', 'success': False}), 401

    return ingest_epv_into_graph(kwargs)
