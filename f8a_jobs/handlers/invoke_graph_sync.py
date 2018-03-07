"""Sync all pending packages to Graph DB."""

from os import environ
import urllib
import concurrent.futures
import requests

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

    BATCH_SIZE = 10

    def _fetch_all_counts(self, params={}):
        url = "%s?%s" % (self._PENDING_API_URL, urllib.parse.urlencode(params))
        self.log.info(url)
        response = requests.get(url)
        self.log.info(response)
        data = response.json()
        all_counts = data["all_counts"]
        self.log.info(data)
        return all_counts

    def _fetch_package_versions(self, params={}, offset=None, limit=None):
        request_params = params.copy()
        request_params.update({"offset": offset, "limit": limit})
        url = "%s?%s" % (self._PENDING_API_URL, urllib.parse.urlencode(request_params))
        self.log.info(url)
        response = requests.get(url)
        self.log.info(response)
        data = response.json()
        return data["pending_list"]

    def _perform_sync(self, packages_list):
        self.log.info("Invoke graph importer at url: '%s' for %s", self._INGEST_API_URL,
                      packages_list)
        response = requests.post(self._INGEST_API_URL, json=packages_list)

        if response.status_code != 200:
            raise RuntimeError("Failed to invoke graph import at '%s' for %s" % (
                self._INGEST_API_URL, packages_list))

        self.log.info("Graph import succeeded with response: %s", response.text)

    def execute(self, **kwargs):
        """Start the synchronization of all finished analyses to Graph database."""

        # fetch count of pending list
        #
        # fetch windowed pending list from backend
        # start with offset at 0, batch_size = BATCH_SIZE
        # while there are more records
        # batch = fetch current batch
        # schedule graph sync for current batch
        # increase offset by query_slice
        # end
        self.log.info(kwargs)

        future_to_params_map = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            all_counts = self._fetch_all_counts(params=kwargs)
            self.log.info(all_counts)
            offset = 0
            while all_counts > offset:
                # for each batch of packages, send request to backend for ingesting this batch

                # package_list = [
                #     {'ecosystem': 'npm', 'name': 'serve-static', 'version': '1.1.7'},...
                # ]
                packages_list = self._fetch_package_versions(params=kwargs, offset=offset,
                                                             limit=self.BATCH_SIZE)
                executor.submit(self._perform_sync, packages_list)
                offset += self.BATCH_SIZE

            for future in concurrent.futures.as_completed(future_to_params_map):
                request_data = future_to_params_map[future]
                try:
                    response_data = future.result()
                except Exception as exc:
                    print("FAILURE: %s" % response_data)
                    print('%r generated an exception: %s' % (response_data, exc))
                else:
                    print("SUCCESS: %s" % request_data)
