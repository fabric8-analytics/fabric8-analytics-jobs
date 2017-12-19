"""Class to aggregate package names from GitHub manifests."""

from selinon import StoragePool
from f8a_jobs.handlers.base import BaseHandler
from f8a_worker.storages import AmazonS3


class AggregateGitHubManifestPackages(BaseHandler):
    """Class to aggregate package names from GitHub manifests."""

    def execute(self, repositories, ecosystem, bucket_name, object_key):
        """Perform aggregation of package names from GitHub manifests.

        :param repositories: a list of repositories
        :param ecosystem: ecosystem, will appear in the resulting JSON file
        :param bucket_name: name of the bucket where to put the resulting JSON file
        :param object_key: object key of the resulting JSON file
        """
        s3 = StoragePool.get_connected_storage('S3GitHubManifestMetadata')

        package_list = []
        tagger_list = []
        manifest_list = []
        for repo in repositories:

            try:
                repo_ecosystem = repo['ecosystem']
                repo_name = repo['repo_name']
            except ValueError:
                self.log.error('Invalid configuration, skipping: {config}'.format(
                    config=str(repo)))
                continue

            try:
                obj = '{e}/{repo_name}/dependency_snapshot.json'.format(
                    e=repo_ecosystem, repo_name=repo_name.replace('/', ':'))
                dependency_snapshot = s3.retrieve_dict(obj)

                dependencies = dependency_snapshot.get('details', {}).get('runtime', [])

                packages = list({x.get('name') for x in dependencies})
                if packages:
                    package_list.append(packages)

                    append_manifest = self._create_manifest_entry(
                        packages,
                        repo_ecosystem,
                        repo_name,
                        s3
                    )
                    manifest_list.append(append_manifest)

                packages_version = dict([(x.get("name"), x.get("version")) for x in dependencies])
                if packages_version:
                    extracted_tagger_list = self._create_tagger_list(ecosystem, packages_version)
                    for etl in extracted_tagger_list:
                        tagger_list.append(etl)

            except Exception as e:
                self.log.error('Unable to collect dependencies for {repo_name}: {reason}'.format(
                    repo_name=repo_name, reason=str(e)))
                continue

        results = {
            'ecosystem': ecosystem,
            'package_list': package_list
        }

        self.log.info("Storing aggregated list of packages in S3")

        manifest_result = {
            "ecosystem": ecosystem,
            "package_list": manifest_list
        }

        s3_dest = AmazonS3(bucket_name=bucket_name)
        s3_dest.connect()
        s3_dest.store_dict(results, object_key)
        s3_dest.store_dict(tagger_list, "tagger_list" + object_key)
        s3_dest.store_dict(manifest_result, "new_manifest" + object_key)

    def _create_tagger_list(self, ecosystem, package_version):
        """Create list of dict objects that is to be appended into tagger_list.

        :param ecosystem: ecosystem name, will appear in json
        :param package_version: a list of tuples containg package name and version;
        :return: a list of dict objects will get appended in tagger_list
        """
        appended_tagger_list = []
        for package in package_version.items():
            appended_tagger_list.append(self._create_data_structure(ecosystem, package[0],
                                                                    package[1]))
        return appended_tagger_list

    def _create_data_structure(self, ecosystem, package, version):
        """Create data structure that describes job configuration.

        :param ecosystem: ecosystem name will appear in each dict object in json file
        :param package: package name for the dict object
        :param version: version of the package for the dict object
        :return: a dict object with required fields
        """
        data = {
            "ecosystem": ecosystem,
            "force": True,
            "force_graph_sync": True,
            "name": package,
            "recursive_limit": 0,
            "version": version
        }
        return data

    def _create_manifest_entry(self, package_list, repo_ecosystem, repo_name, s3):
        """Create dict object for the given repository with metadata taken from the S3 database.

        :param package_list: list of dependencies of a repo.
        :param repo_ecosystem: ecosystem of repo.
        :param repo_name: name of the repo.
        :param s3: connection of storage (bucket)
        :return: one dict. object of repo. as per requirement of aggregated manifest file
        """
        add_manifest = {'repo_name': repo_name}
        try:
            obj = '{e}/{repo_name}/github_details.json'.\
                format(e=repo_ecosystem, repo_name=repo_name.replace('/', ':'))
            github_details = s3.retrieve_dict(obj)
            github_stats = github_details.get("details", {})
            if github_stats:
                github_stats_data = {
                    "stars": github_stats.get("stargazers_count"),
                    "watches": github_stats.get("subscribers_count"),
                    "forks": github_stats.get("forks_count"),
                    "contributors": github_stats.get("contributors_count")
                }
                add_manifest["github_stats"] = github_stats_data
                pkg_list_new = {
                    "path_to_pom": "",
                    "dependency_list": package_list
                }
                add_manifest["all_poms_found"] = pkg_list_new

        except Exception as e:
            self.log.exception('Unable to collect github details for {repo_name}: {reason}'.
                               format(repo_name=repo_name, reason=str(e)))
        return add_manifest
