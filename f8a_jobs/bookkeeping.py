"""Module that contains functions for EPV ingestion in Graph DB."""

from selinon import run_flow, run_flow_selective
import logging
import os
from f8a_jobs.utils import requires_auth
from f8a_utils.gh_utils import GithubUtils
from f8a_utils.tree_generator import GolangDependencyTreeGenerator
import time

logger = logging.getLogger(__name__)

_INVOKE_API_WORKERS = os.environ.get('INVOKE_API_WORKERS', 'True') == 'True'
_DISABLE_UNKNOWN_PACKAGE_FLOW = os.environ.get('DISABLE_UNKNOWN_PACKAGE_FLOW', 'False') == 'True'


def create_component_bookkeeping(analysis_details):

    input_data = analysis_details.get('body', {})
    # Check if worker flow activation is disabled.
    if not _INVOKE_API_WORKERS:
        logger.debug('Worker flows are disabled.')
        input_data['message'] = 'Worker flows are disabled.'
        return input_data, 201
    flow_name = input_data.get('flowname')
    node_arguments = input_data.get('data')
    try:
        dispacher_id = run_flow(flow_name, node_arguments)
        item['dispacher_id'] = dispacher_id.id
    except Exception as e:
        return {'message': 'Failed to initiate worker flow.'}, 500
    return "Incorrect data sent", 201

@requires_auth
def component_bookkeeping(**kwargs):
    """To handle POST requests for end point '/ingestions/component-bookkeeping'."""
    return create_component_bookkeeping(kwargs)


def component_bookkeeping_internal(**kwargs):
    """To handle POST requests for end point '/ingestions/component-bookkeeping'."""
    return create_component_bookkeeping(kwargs)