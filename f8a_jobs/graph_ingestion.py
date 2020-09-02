"""Module that contains functions for EPV ingestion in Graph DB."""

from selinon import run_flow
import logging
import f8a_jobs.defaults as defaults
import flask

logger = logging.getLogger(__name__)


def ingest_epv_into_graph(epv_details, headers=None):
    """Handle POST requests for triggering ingestion flow."""
    try:
        input_json = epv_details.get('epv_details', {})
        logger.info('/api/v1/ingest-epv is called for {}.'.format(input_json))

        auth_token = headers.get('auth_token', '')

        if auth_token != defaults.APP_SECRET_KEY:
            return flask.jsonify({"message": "Unauthorized!!", 'success': False}), 401

        if input_json and 'flow_arguments' in input_json and 'flow_name' in input_json:
            flow_name = input_json['flow_name']
            flow_args = input_json['flow_arguments']

            resp = {}
            dispacher_ids = []

            for args in flow_args:
                dispacher_id = run_server_flow(flow_name, args)
                dispacher_ids.append(dispacher_id.id)
                logger.info('{} initiated for {}'.format(flow_name, args))

            resp['dispacher_ids'] = dispacher_ids
            resp['message'] = 'All ingestion flows are initiated'
            resp['success'] = True
            return flask.jsonify(resp), 201
        else:
            logger.info('Incorrect data sent for the flow: {p}'.format(p=input_json))
            return flask.jsonify({"message": "Incorrect data sent.", 'success': False}), 400
    except Exception as e:
        logger.error("Exception while initiating the worker flow {}".format(e))
        return flask.jsonify({'message': 'Failed to initiate worker flow.', 'success': False}), 500


def run_server_flow(flow_name, flow_args):
    """To run the worker flow via selinon."""
    return run_flow(flow_name, flow_args)
