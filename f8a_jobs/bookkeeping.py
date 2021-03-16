"""Module that contains functions for EPV ingestion in Graph DB."""

from selinon import run_flow
import logging
import os
from f8a_jobs.utils import requires_auth

logger = logging.getLogger(__name__)

_INVOKE_API_WORKERS = os.environ.get('INVOKE_API_WORKERS', 'True') == 'True'


def create_component_bookkeeping(analysis_details):
    """Handle implementation of API for triggering componentApi flow."""
    input_data = analysis_details.get('body', {})
    # Check if worker flow activation is disabled.
    if not _INVOKE_API_WORKERS:
        logger.debug('Worker flows are disabled.')
        input_data['message'] = 'Worker flows are disabled.'
        return input_data, 201
    flow_name = input_data.get('flowname')
    node_arguments = input_data
    try:
        dispacher_id = run_flow(flow_name, node_arguments)
        input_data['dispacher_id'] = dispacher_id.id
    except Exception as e:
        logger.error('Exception while initiating the worker flow %s', e)
        return {'message': 'Failed to initiate worker flow.'}, 500
    return input_data, 201


@requires_auth
def trigger_workerflow(**kwargs):
    """To handle POST requests for end point '/ingestions/trigger-workerflow'."""
    return create_component_bookkeeping(kwargs)


def trigger_workerflow_internal(**kwargs):
    """To handle POST requests for end point '/internal/ingestions/trigger-workerflow'."""
    return create_component_bookkeeping(kwargs)
