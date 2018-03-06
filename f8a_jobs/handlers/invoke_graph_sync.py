"""Sync all pending packages to Graph DB."""

from sqlalchemy.exc import SQLAlchemyError
from f8a_worker.models import Analysis, Package, Version, Ecosystem
from f8a_worker.workers import GraphImporterTask
from f8a_worker.base import BaseTask
import requests
from os import environ
import urllib


from .base import BaseHandler


class InvokeGraphSync(BaseHandler):
    """Sync all finished analyses to Graph DB."""

    _SERVICE_HOST = environ.get("BAYESIAN_DATA_IMPORTER_SERVICE_HOST", "bayesian-data-importer")
    _SERVICE_PORT = environ.get("BAYESIAN_DATA_IMPORTER_SERVICE_PORT", "9192")
    _PENDING_API_ENDPOINT = "api/v1/pending"
    _SYNC_ALL_ENDPOINT = "api/v1/sync_all"
    _INGEST_SERVICE_ENDPOINT = "api/v1/ingest_to_graph"

    _PENDING_API_URL = "http://{host}:{port}/{endpoint}".format(
        host=_SERVICE_HOST, port=_SERVICE_PORT, endpoint=_PENDING_API_ENDPOINT)

    _SYNC_ALL_API_URL = "http://{host}:{port}/{endpoint}".format(
        host=_SERVICE_HOST, port=_SERVICE_PORT, endpoint=_SYNC_ALL_ENDPOINT)

    _INGEST_API_URL = "http://{host}:{port}/{endpoint}".format(
        host=_SERVICE_HOST, port=_SERVICE_PORT, endpoint=_INGEST_SERVICE_ENDPOINT)

    query_slice = 10

    def _fetch_all_counts(self, params={}):
        url = "%s/?%s" % (self._PENDING_API_URL, urllib.parse.urlencode(params))
        response = requests.get(url)
        data = response.json()
        all_counts = data["all_counts"]
        return all_counts

    def _fetch_package_versions(self, params={}, offset=None, limit=None):
        url = "%s/?%s" % (self._PENDING_API_URL, urllib.parse.urlencode(params))
        response = requests.get(url)
        data = response.json()
        return data["pending_list"]

    def execute(self, **kwargs):
        """Start the synchronization of all finished analyses to Graph database."""

        # fetch count of pending list
        #
        # fetch windowed pending list from backend
        # start with offset at 0, batch_size = query_slice
        # while there are more records
        # batch = fetch current batch
        # schedule graph sync for current batch
        # increase offset by query_slice
        # end

        all_counts = self._fetch_all_counts(params)
        offset = 0
        while all_counts > 0:
            # for each batch of packages, send request to backend for ingesting this batch

            # package_list = [
            #     {'ecosystem': 'npm', 'name': 'serve-static', 'version': '1.1.7'},...
            # ]
            packages_list = self._fetch_package_versions(params=kwargs, offset=offset,
                                         limit=self.query_slice)

            self.log.info("Invoke graph importer at url: '%s' for %s", self._INGEST_API_URL,
                          packages_list)
            # response = requests.post(self._INGEST_API_URL, json=packages_list)
            #
            # if response.status_code != 200:
            #     raise RuntimeError("Failed to invoke graph import at '%s' for %s" % (
            #         self._INGEST_API_URL, packages_list))

            # self.log.info("Graph import succeeded with response: %s", response.text)
            offset += self.query_slice


