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
        return 'Worker flows are disabled.', 201
    flow_name = input_data.get('flowname')
    node_arguments = input_data
    try:
        dispacher_id = run_flow(flow_name, node_arguments)
    except Exception as e:
        logger.error('Exception while initiating the worker flow %s', e)
        return 'Failed to initiate worker flow.', 500
    return str(dispacher_id.id), 201


@requires_auth
def component_bookkeeping(**kwargs):
    """To handle POST requests for end point '/ingestions/component-bookkeeping'."""
    return create_component_bookkeeping(kwargs)


def component_bookkeeping_internal(**kwargs):
    """To handle POST requests for end point '/ingestions/component-bookkeeping'."""
    return create_component_bookkeeping(kwargs)
