"""Job to read tags from graph and apply a verification logic on them."""

from botocore.exceptions import ClientError
import json
import os
from selinon import StoragePool
from f8a_worker.utils import get_session_retry
from f8a_jobs.handlers.base import BaseHandler


class AggregateCrowdSourceTags(BaseHandler):
    """Job to read tags from graph and apply a verification logic on them."""

    def execute(self, ecosystem):
        """Process raw-tags and update existing package_topic.json file on S3.

        :param ecosystem: Name of ecosystem
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

        results = self._update_tags_from_graph(ecosystem=ecosystem, results=results)

        s3.store_package_topic(ecosystem, results)
        self.log.debug("The file crowd_sourcing_package_topic.json "
                       "has been stored for %s", ecosystem)

    def _get_graph_url(self):
        """Get graph database url."""
        url = "http://{host}:{port}".\
            format(host=os.getenv("BAYESIAN_GREMLIN_HTTP_SERVICE_HOST", "localhost"),
                   port=os.getenv("BAYESIAN_GREMLIN_HTTP_SERVICE_PORT", "8182"))
        self.log.debug("Graph url is: {}".format(url))
        return url

    def _execute_query(self, query):
        """Run the graph query."""
        payload = {'gremlin': query}
        graph_url = self._get_graph_url()
        self.log.debug(query)
        response = get_session_retry().post(graph_url, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()
        else:
            self.log.error('Graph is not responding.')
            return {}

    @staticmethod
    def _get_usertags_query(ecosystem, usercount):
        """Create a gremlin-query to fetch tags suggested by end-user.

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

    @staticmethod
    def _set_user_tags_query(ecosystem, pkg_name, tags):
        """Create gremlin-query to aggregate raw tags as an user tags.

        :param ecosystem: Name of the ecosystem
        :param pkg_name: Package name
        :param tags: Processed tags list
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

    @staticmethod
    def _set_usercount_query(ecosystem, pkg_name, tags):
        """Create gremlin-query to set tags into graph and make manual tagging requirement false.

        :param ecosystem: Name of the ecosystem
        :param pkg_name: Package name
        :param tags: Processed tags list
        """
        query = "g.V()." \
                "has('ecosystem', '{ecosystem}')." \
                "has('name', '{pkg_name}')." \
                "properties('tags').drop().iterate();" \
                "pkg = g.V().has('ecosystem', '{ecosystem}')." \
                "has('name', '{pkg_name}').next();" \
                "pkg.property('manual_tagging_required', false);"\
            .format(ecosystem=ecosystem, pkg_name=pkg_name)
        query += "".join(["pkg.property('tags', '{}');".format(t) for t in tags])
        return query

    def _update_tags_from_graph(self, ecosystem, results):
        """Read user-tags from graph, process tags, update graph and return updated package topics.

        :param ecosystem: ecosystem name
        :param results: package topics map
        """
        usercount = os.getenv("CROWDSOURCE_USER_COUNT", 2)
        query = self._get_usertags_query(ecosystem=ecosystem, usercount=usercount)
        correct_data = self._execute_query(query=query)
        package_topic_list = results
        graph_data = correct_data.get("result", {}).get("data", [])
        if graph_data:
            query = ""
            for user_tags_data in graph_data:
                user_tags = user_tags_data.get("user_tags", [])
                pkg_name = user_tags_data["name"][0]
                pkg_tags, raw_tags = self.filter_user_tags(user_tags=user_tags)
                if not pkg_tags:
                    query += self._set_user_tags_query(ecosystem=ecosystem,
                                                       pkg_name=pkg_name,
                                                       tags=raw_tags)
                else:
                    query += self._set_usercount_query(ecosystem=ecosystem,
                                                       pkg_name=pkg_name,
                                                       tags=pkg_tags)
                package_topic_list[pkg_name] = pkg_tags
            self._execute_query(query)
            self.log.info("Package in the Graph has been updated")
        results = {
            "ecosystem": ecosystem,
            "package_topic_map": package_topic_list
        }
        return results

    @staticmethod
    def filter_user_tags(user_tags):
        """Filter tags and apply verification logic on it.

        :param user_tags: list of tags provided by end-users for one package
        :return: pkg_tags for package_topic_map, raw_tags to update graph
        """
        pkg_tags = set()
        raw_tags = set()
        for user_tags_ in user_tags:
            tags = AggregateCrowdSourceTags.process_tags(user_tags_)
            raw_tags = raw_tags | tags
            if not pkg_tags:
                pkg_tags = tags
            else:
                pkg_tags = pkg_tags & tags
        return list(pkg_tags), list(raw_tags)

    @staticmethod
    def process_tags(user_tags):
        """Preprocessing and data cleansing of raw-tags.

        Currently we just split the string into a set of individual tags.
        TODO: The processing should consist of
              - filtering out punctuation from tags
              - filtering out stop-words from tags
              - performing stemming on tags
        :param user_tags: semicolon separated string with end-user suggested raw-tags
        :return set of cleaned tags
        """
        return set(user_tags.split(";"))
