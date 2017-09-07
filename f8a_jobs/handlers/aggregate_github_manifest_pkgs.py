from selinon import StoragePool
from f8a_jobs.handlers.base import BaseHandler
from f8a_worker.storages import AmazonS3


class AggregateGitHubManifestPackages(BaseHandler):

    def execute(self, repositories, ecosystem, bucket_name, object_key):
        """ Aggregate package names from GitHub manifests.

        :param repositories: a list of repositories
        :param ecosystem: ecosystem, will appear in the resulting JSON file
        :param bucket_name: name of the bucket where to put the resulting JSON file
        :param object_key: object key of the resulting JSON file
        """

        s3 = StoragePool.get_connected_storage('S3GitHubManifestMetadata')

        package_list = []
        for repo in repositories:

            try:
                repo_ecosystem = repo['ecosystem']
                repo_name = repo['repo_name']
            except ValueError:
                self.log.error('Invalid configuration, skipping: {config}'.format(config=str(repo)))
                continue

            try:
                obj = '{e}/{repo_name}/dependency_snapshot.json'.format(e=repo_ecosystem,
                                                                        repo_name=repo_name.replace('/', ':'))
                dependency_snapshot = s3.retrieve_dict(obj)

                dependencies = dependency_snapshot.get('details', {}).get('runtime', [])

                packages = list({x.get('name') for x in dependencies})
                if packages:
                    package_list.append(packages)

            except Exception as e:
                self.log.error('Unable to collect dependencies for {repo_name}: {reason}'.format(repo_name=repo_name,
                                                                                                 reason=str(e)))
                continue

        results = {
            'ecosystem': ecosystem,
            'package_list': package_list
        }

        self.log.info("Storing aggregated list of packages in S3")

        s3_dest = AmazonS3(bucket_name=bucket_name)
        s3_dest.connect()
        s3_dest.store_dict(results, object_key)
