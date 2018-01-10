"""Class to append new data for Kronos training."""

from selinon import StoragePool
from sqlalchemy.exc import SQLAlchemyError
from selinon import StoragePool
from f8a_worker.storages import AmazonS3
from .base import BaseHandler
import os


class KronosDataUpdater(BaseHandler):
    """Class to append new data for Kronos training."""

    _MANIFEST_PATH = "github/data_input_manifest_file_list"
    _PACKAGE_TOPIC_PATH = "github/data_input_raw_package_list/package_topic.json"
    _MANIFEST_FILE = "manifest.json"

    def __init__(self, *args, **kwargs):
        """Initialize instance of the GitHubMostStarred class."""
        super().__init__(*args, **kwargs)
        self.ecosystem = None
        self.user_persona = None
        self.extra_manifest_list = []
        self.unique_packages = set()
        self.past_days = None

    def execute(self, bucket_name="dev-stack-analysis-clean-data",
                ecosystem="maven",
                user_persona=1,
                past_days=7):
        """Append new data for Kronos training.

        :param bucket_name: The source where data is to be added.
        :param ecosystem: The ecosystem for which data is to be added.
        :param user_persona: The User type for which data is to be added.
        :param past_days: The number of days for sync.
        """
        self.ecosystem = str(ecosystem)
        self.past_days = int(past_days)
        self.user_persona = str(user_persona)
        return self._processing()

    def _generate_query(self):
        """Generate Query to fetch required data."""
        query = "SELECT all_details -> 'ecosystem' as ecosystem," \
            "all_details -> '_resolved' as deps from worker_results" \
            " cross join jsonb_array_elements" \
            "(worker_results.task_result -> 'result')" \
            " all_results cross join jsonb_array_elements" \
            "(all_results -> 'details') all_details where worker = 'GraphAggregatorTask'" \
            " and EXTRACT(DAYS FROM age(to_timestamp" \
            "(task_result->'_audit'->>'started_at','YYYY-MM-DDThh24:mi:ss')))" \
            "<={} and all_details->>'ecosystem'='{}';".format(
                self.past_days, self.ecosystem)
        self.log.info("Genrated Query is \n {}".format(query))
        return query

    def _execute_query(self, query):
        """Execute the query and return the ResultProxy."""
        return self.postgres.session.execute(query)

    def _append_mainfest(self, s3):
        """For each extra manifest list, append it to existing list.

        :param s3: The S3 datastore object.
        """
        manifest_path = os.path.join(self.ecosystem,
                                     _MANIFEST_PATH,
                                     self.user_persona, _MANIFEST_FILE)
        manifest_data = s3.fetch_existing_data(manifest_path)
        for each in manifest_data:
            if each.get('ecosystem') == self.ecosystem:
                cur_package_list = each.get('package_list', [])
                cur_package_list.extend(self.extra_manifest_list)
                each['package_list'] = cur_package_list
                break
        s3.store_updated_data(manifest_data, manifest_path)

    def _append_package_topic(self, s3):
        """For each extra package, append it to existing package_topic.

        Default topic list for new packages is an empty list [].
        :param s3: The S3 datastore object.
        """
        package_topic_path = os.path.join(self.ecosystem,
                                          _PACKAGE_TOPIC_PATH)
        package_topic = s3.fetch_existing_data(package_topic_path)
        for each in package_topic:
            if each.get('ecosystem') == self.ecosystem:
                cur_package_list = each.get('package_topic_map', {})
                for each_package in self.unique_packages:
                    if each_package not in cur_package_list:
                        cur_package_list[each_pck] = []
                each['package_list'] = cur_package_list
                break
        s3.store_updated_data(package_topic, package_topic_path)

    def _processing(self):
        """Append new data for Kronos training."""
        try:
            s3 = StoragePool.get_connected_storage('S3KronosAppend')
            result = self._execute_query(self._generate_query()).fetchall()
            result_len = len(result)
            self.log.info("Query executed.")
            self.log.info("Number of results = {}".format(result_len))
            if result_len > 0:
                for each_row in result:
                    package_list = []
                    if len(each_row) != 2 or each_row[0] != self.ecosystem:
                        continue
                    for dep in each_row[1]:
                        package_name = dep.get('package')
                        package_list.append(package_name)
                        self.unique_packages.add(package_name)
                        self.extra_manifest_list.append(package_list)

                self._append_mainfest(s3)
                self._append_package_topic(s3)
                self.log.info("User Input Stacks appended.")
        except Exception as e:
            self.log.exception('Unable to append input stack for ecosystem {ecosystem}: {reason}'.
                               format(ecosystem=self.ecosystem, reason=str(e)))
