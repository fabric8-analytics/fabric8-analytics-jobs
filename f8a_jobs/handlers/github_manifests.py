import urllib.parse
from selinon import StoragePool
from f8a_jobs.handlers.base import BaseHandler


class GitHubManifests(BaseHandler):

    GITHUB_URL = 'https://github.com/'

    def execute(self, repositories, skip_if_exists):
        """Collect and process manifest files from given GitHub repositories.

        :param repositories: a list of repositories to process, with flow arguments
        :param skip_if_exists: a list of flow arguments per flow
        """
        s3 = StoragePool.get_connected_storage('S3GitHubManifestMetadata')

        for repo in repositories:

            try:
                ecosystem = repo['ecosystem']
                repo_name = repo['repo_name']
            except ValueError:
                self.log.error('Invalid configuration, skipping: {config}'.format(config=str(repo)))
                continue

            if skip_if_exists:
                metadata_object_name = s3.get_object_key_path(ecosystem, repo_name) + \
                    '/metadata.json'
                if s3.object_exists(metadata_object_name):
                    self.log.info('Results for repo {repo} already exist, skipping.'.format(
                        repo=repo['repo_name']))
                    continue

            repo_url = urllib.parse.urljoin(self.GITHUB_URL, repo['repo_name'] + '.git')
            node_args = dict(
                ecosystem=ecosystem,
                force=repo.get('force', False),
                force_graph_sync=repo.get('force_graph_sync', False),
                repo_name=repo_name,
                url=repo_url
            )
            if repo.get('recursive_limit') is not None:
                node_args['recursive_limit'] = repo.get('recursive_limit')

            self.log.debug('Scheduling analysis for GitHub repository {repo}'.format(
                repo=repo['repo_name']))
            self.run_selinon_flow('githubManifestMetadataFlow', node_args)
