"""Functions to retrieve pending list and invoke Graph Sync."""

import f8a_jobs.defaults as configuration
import requests
import traceback
import logging


logger = logging.getLogger(__name__)


def _api_call(url, params={}):
    url = "%s%s" % (configuration.DATA_IMPORTER_ENDPOINT, "/api/v1/pending")
    try:
        logger.info("API Call for url: %s, params: %s" % (url, params))
        r = requests.get(url, params=params)
        if r is None:
            logger.error("Returned response is: %s" % r)
            raise Exception("Empty response found")

        result = {"data": r.json()}
    except Exception:
        logger.error(traceback.format_exc())
        result = {"error": "Failed to retrieve data from Data Model Importer backend"}
    return result


def fetch_pending(params={}):
    url = "%s%s" % (configuration.DATA_IMPORTER_ENDPOINT, "/api/v1/pending")
    return _api_call(url, params)


def invoke_sync(params={}):
    url = "%s%s" % (configuration.DATA_IMPORTER_ENDPOINT, "/api/v1/sync_all")
    return _api_call(url, params)
