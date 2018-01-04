from botocore.exceptions import ClientError
import json
import os
from selinon import StoragePool
from f8a_worker.utils import get_session_retry
from f8a_jobs.handlers.base import BaseHandler


class AggregateCrowdSourceTags(BaseHandler):

    def execute(self, ecosystem):
        """
        Process raw-tags and update the existing package_topic.json file in S3 bucket
        :param ecosystem: Name of ecosystem
        :return: Updated package_topic.json file
        """
        s3 = StoragePool.get_connected_storage('S3CrowdSourceTags')

        package_topic = []
        try:
            package_topic = s3.retrieve_package_topic(ecosystem)
        except ClientError:
            self.log.error("Unable to retrieve package_topic.json for %s", ecosystem)

        results = {}
        for record in package_topic:
            if record.get("ecosystem") == ecosystem and record.get("package_topic_map"):
                results = record["package_topic_map"]
        if not results:
            self.log.error("Unable to retrieve package_topic_map for %s", ecosystem)

        results = self._read_tags_from_graph(ecosystem=ecosystem, results=results)

        s3.store_package_topic(ecosystem, results)
        self.log.debug("The file crowd_sourcing_package_topic.json "
                       "has been stored for %s", ecosystem)

    def _get_graph_url(self):
        """
         Provide the graph database url
         :return: graph-url
         """
        url = "http://{host}:{port}".\
            format(host=os.getenv("BAYESIAN_GREMLIN_HTTP_SERVICE_HOST", "localhost"),
                   port=os.getenv("BAYESIAN_GREMLIN_HTTP_SERVICE_PORT", "8182"))
        self.log.debug("Graph url is: {}".format(url))
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
            self.log.error('Graph is not responding.')
            return {}

    def _get_usertags_query(self, ecosystem, usercount):
        """
        Create a gremlin-query to fetch tags suggested by end-user
        :param ecosystem: name of the ecosystem
        :param usercount: number of end-user who has suggested had tags
        :return: gremlin-query to fetch package-names, user-count and raw-tags
        """
        query = "g.V()." \
                "has('ecosystem', '{ecosystem}')." \
                "has('manual_tagging_required', 'true')." \
                "has('tags_count','{usercount}').valueMap()"\
                .format(ecosystem=ecosystem, usercount=usercount)
        return query

    def _set_user_tags_query(self, ecosystem, pkg_name, tags):
        """
        When pkg_tags is empty,
        Create gremlin-query to aggregate raw tags as an user tags
        :param ecosystem: Name of the ecosystem
        :param pkg_name: Package name
        :param tags: Processed tags list
        :return: gremlin-query to append tags into graph
        """
        query = "g.V()." \
                "has('ecosystem', '{ecosystem}')." \
                "has('name', '{pkg_name}')." \
                "properties('tags').drop().iterate();" \
                "pkg = g.V().has('ecosystem', '{ecosystem}')." \
                "has('name', '{pkg_name}').next();" \
                "pkg.property('manual_tagging_required', true);" \
                "pkg.property('tags_count', 1);".format(ecosystem=ecosystem,
                                                        pkg_name=pkg_name)
        query += "".join(["pkg.property('tags', '{}');".format(t) for t in tags])
        return query

    def _set_usercount_query(self, ecosystem, pkg_name, tags):
        """
        When pkg_tags is not empty, Create gremlin-query to rest
        the manual_tagging_requirement property false after successful
        tagging of a package.
        :param ecosystem: Name of the ecosystem
        :param pkg_name: Package name
        :param tags: Processed tags list
        :return: gremlin-query to set tags into graph and make manual tagging requirement false
        """
        query = "g.V()." \
                "has('ecosystem', '{ecosystem}')." \
                "has('name', '{pkg_name}')." \
                "properties('tags').drop().iterate();" \
                "pkg = g.V().has('ecosystem', '{ecosystem}')." \
                "has('name', '{pkg_name}').next();" \
                "pkg.property('manual_tagging_required', false);"\
            .format(ecosystem=ecosystem,pkg_name=pkg_name)
        query += "".join(["pkg.property('tags', '{}');".format(t) for t in tags])
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
                pkg_name = users_tag_data["name"][0]
                pkg_tags, raw_tags = self._filter_users_tag(users_tag=users_tag)
                if not pkg_tags:
                    query += self._set_user_tags_query(ecosystem=ecosystem,
                                                       pkg_name=pkg_name,
                                                       tags=raw_tags)
                else:
                    query += self._set_usercount_query(ecosystem=ecosystem,
                                                       pkg_name=pkg_name,
                                                       tags=pkg_tags)
                package_topic_list[pkg_name] = list(pkg_tags)
            self._execute_query(query)
            self.log.info("Package in the Graph has been updated")
        results = {
            "ecosystem": ecosystem,
            "package_topic_map": package_topic_list
        }
        return results

    def _filter_users_tag(self, users_tag):
        """
        Filter tags and apply verification logic on it
        :param users_tag: list of tags provided by end-users for one package
        :return: pkg_tags for package_topic_map, raw_tags to update graph
        """
        pkg_tags = set()
        tags = []
        raw_tags = []
        for user_tag in users_tag:
            tags = self._process_tags(user_tag)
            raw_tags.extend(tags)
            if not pkg_tags:
                pkg_tags = set(tags)
            else:
                pkg_tags = pkg_tags & set(tags)
        return pkg_tags, raw_tags

    @staticmethod
    def process_tags(tags):
        """
        Preprocesing and Data cleansing task on raw-tags
        :param tags: End-user suggested raw-tags
        :return: List of cleaned tags
        """
        return tags.split(";")
