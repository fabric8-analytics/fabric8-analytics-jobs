"""Functions to retrieve pending list and invoke Graph Sync."""

import f8a_jobs.defaults as configuration
import requests
import traceback
import logging
from urllib.parse import urljoin


logger = logging.getLogger(__name__)


def _api_call(url, params=None):
    params = params or {}
    try:
        logger.info("API Call for url: %s, params: %s" % (url, params))
        r = requests.get(url, params=params)
        r.raise_for_status()
        result = {"data": r.json()}
    except requests.exceptions.HTTPError:
        logger.error(traceback.format_exc())
        result = {"error": "Failed to retrieve data from Data Model Importer backend"}
    return result


def fetch_pending(params=None):
    params = params or {}
    """Invoke Pending Graph Sync APIs for given parameters."""
    url = urljoin(configuration.DATA_IMPORTER_ENDPOINT, "/api/v1/pending")
    return _api_call(url, params)


def invoke_sync(params=None):
    params = params or {}
    """Invoke Graph Sync APIs to sync for given parameters."""
    url = urljoin(configuration.DATA_IMPORTER_ENDPOINT, "/api/v1/sync_all")
    return _api_call(url, params)
