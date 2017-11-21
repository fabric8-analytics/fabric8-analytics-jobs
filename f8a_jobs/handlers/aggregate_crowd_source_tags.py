from f8a_worker.utils import get_session_retry
import json
import os
from selinon import StoragePool
from f8a_jobs.handlers.base import BaseHandler
from f8a_worker.storages import AmazonS3


class AggregateCrowdSourceTags(BaseHandler):

    def execute(self, ecosystem):
        """
        Process raw-tags and update the existing package_topic.json file in S3 bucket
        :param ecosystem: Name of ecosystem
        :return: Updated package_topic.json file
        """
        s3 = StoragePool.get_connected_storage('S3CrowdSourceTags')
        bucket_name = "{ecosystem}".format(ecosystem=ecosystem) +\
                      "github/data_input_raw_package_list/"
        self.log.info("Connected with S3 bucket: {}", bucket_name)
        results = {}
        try:
            obj = bucket_name + "package_topic.json"
            package_topic = s3.retrieve_dict(obj)
            if package_topic:
                results = package_topic.get("package_topic_map")

        except Exception as e:
            self.log.error('Unable to collect package_topic for {ecosystem}: {reason}'.format(
                ecosystem=ecosystem, reason=str(e)))
        results = self._read_tags_from_graph(ecosystem=ecosystem, results=results)
        s3_dest = AmazonS3(bucket_name=bucket_name)
        s3_dest.connect()
        s3_dest.store_dict(results, "package_topic.json")
        self.log.info("package_topic.json has been updated for ecosystem: {}", ecosystem)

    def _get_graph_url(self):
        """
         Provide the graph database url
         :return: graph-url
         """
        url = "http://{host}:{port}".\
            format(host=os.environ.get("BAYESIAN_GREMLIN_HTTP_SERVICE_HOST", "localhost"),
                   port=os.environ.get("BAYESIAN_GREMLIN_HTTP_SERVICE_PORT", "8182"))
        self.log.info("Graph url is: {}".format(url))
        return url

    def _execute_query(self, query):
        """
        Run the graph queries
        :param query:
        :return: query response
        """
        payload = {'gremlin': query}
        graph_url = self._get_graph_url()
        response = get_session_retry().post(graph_url, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()
        else:
            self.log.info('Graph is not responding.')
            return {}

    def _get_usertags_query(self, ecosystem, usercount):
        """
        Create a gremlin-query to fetch tags suggested by end-user
        :param ecosystem: name of the ecosystem
        :param usercount: number of end-user who has suggested had tags
        :return: gremlin-query to fetch package-names, user-count and raw-tags
        """
        query = "g.V()." \
                "has('ecosystem','" + ecosystem + "')." \
                "has('manual_tagging_required', 'true')." \
                "has('tags_count','" + usercount + "').valueMap()"
        return query

    def _set_usercount_query(self, ecosystem, pkg_name, tags):
        """
        Create gremlin-query to rest the manual_tagging_requirement property false after successful
        tagging of a package.
        :param ecosystem: Name of the ecosystem
        :param pkg_name: Package name
        :param tags: Processed tags list
        :return: gremlin-query to set tags into graph and make manual tagging requirement false
        """
        query = "g.V()." \
                "has('ecosystem', '" + ecosystem + "')." \
                "has('name', '" + pkg_name + "')." \
                "properties('tags').drop().iterate();" \
                " g.V().has('ecosystem', '" + ecosystem + "')." \
                "has('name', '" + pkg_name + "')." \
                "property('manual_tagging_required', false)." \
                "property('tags','" + tags + "');"
        return query

    def _read_tags_from_graph(self, ecosystem, results):
        """
        Read user-tags from graph, process tags, update graph and return package_topic file
        :param ecosystem: ecosystem name
        :param results: package topics map
        :return:
        """
        usercount = os.environ.get("CROWDSOURCE_USER_COUNT", 2)
        query = self._get_usertags_query(ecosystem=ecosystem, usercount=usercount)
        correct_data = self._execute_query(query=query)
        package_topic_list = results
        graph_data = correct_data.get("result", {}).get("data", [])
        if graph_data:
            query = ""
            for users_tag_data in graph_data:
                users_tag = users_tag_data.get("user_tags", [])
                pkg_name = users_tag_data.get("name")[0]
                pkg_tags = []
                tags = []
                for user_tag in users_tag:
                    tags = self._process_tags(user_tag)
                    if pkg_tags == []:
                        pkg_tags = set(tags)
                    else:
                        pkg_tags = pkg_tags & set(user_tag)
                query += self._set_usercount_query \
                    (ecosystem=ecosystem, pkg_name=pkg_name, tags=pkg_tags)
                package_topic_list[pkg_name] = list(pkg_tags)
            self._execute_query(query)
            self.log.info("Package in the Graph has been updated")
        results = {
            "ecosystem": ecosystem,
            "package_topic_map": package_topic_list
        }
        return results

    def _process_tags(self, tags):
        """
        Preprocesing and Data cleansing task on raw-tags
        :param tags: End-user suggested raw-tags
        :return: List of cleaned tags
        """
        tag_list = []
        for tag in tags.split(";"):
            tag_list.append(tag)
        return tag_list
