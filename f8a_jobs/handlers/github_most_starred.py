import requests
import urllib.parse
from selinon import StoragePool
from .base import BaseHandler

import f8a_jobs.defaults as configuration


class GitHubMostStarred(BaseHandler):
    """ Store metadata of most starred <insert-your-favourite-ecosystem> projects
    on GitHub to an S3 bucket. """

    GITHUB_API_URL = 'https://api.github.com/'
    GITHUB_URL = 'https://github.com/'

    # ecosystem->(GitHub-language, supported-manifest) mapping
    _ECOSYSTEM_DETAILS = {'maven': ('java', 'pom.xml'),
                          'npm': ('javascript', 'package.json'),
                          'pypi': ('python', 'requirements.txt')}

    _MIN_STARS_DEFAULT = 500

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nversions = 1
        self.count = 1
        self.force = False
        self.recursive_limit = None
        self.ecosystem = None
        self.min_stars = None
        self.max_stars = None
        self.skip_if_exists = True
        self.start_from = 0

    def _get_stars_filter(self):
        if self.min_stars is not None and self.max_stars is not None:
            return '{min}..{max}'.format(min=self.min_stars, max=self.max_stars)
        elif self.max_stars is not None:
            return '<={max}'.format(max=self.max_stars)
        else:
            return '>={min}'.format(min=self.min_stars or self._MIN_STARS_DEFAULT)

    def get_most_starred_repositories(self, ecosystem, start_from):
        url_path = 'search/repositories?q=language:{lang}+stars:{stars}+sort:stars&page={page}'
        url_template = urllib.parse.urljoin(self.GITHUB_API_URL, url_path)

        skip = start_from % 100
        page = 1 + (start_from // 100)
        repos = []

        def get(lang, page_number):
            url = url_template.format(lang=lang, stars=self._get_stars_filter(), page=page_number)
            response = requests.get(url, params={'access_token': configuration.GITHUB_ACCESS_TOKEN})
            result = []
            if response.status_code == 200:
                content = response.json()
                # there is 100 results at most
                result = [x['full_name'] for x in content.get('items', [])]
            else:
                self.log.error('GET on %s returned %s', url, str(response.status_code))
            return result

        while True:
            if not repos:
                repos = get(self._ECOSYSTEM_DETAILS[ecosystem][0], page)
                page += 1
                if not repos:
                    raise StopIteration

            if skip:
                skip_slice = skip if skip < len(repos) else len(repos)
                repos = repos[skip_slice:]
                skip -= skip_slice

            repo_name = repos.pop(0)

            # we need to check that the repository contains manifest file that mercator can process;
            # for example not all "Java" repositories have pom files
            # TODO: if this is too slow, switch to BigQuery
            repo_url = urllib.parse.urljoin(self.GITHUB_URL, repo_name + '/')
            manifest_url = urllib.parse.urljoin(repo_url, 'blob/master/' + self._ECOSYSTEM_DETAILS[ecosystem][1])
            head_response = requests.head(manifest_url)
            if not head_response.status_code == 200:
                self.log.debug('Missing or unknown manifest file in GitHub repo %s', repo_name)
                continue
            yield repo_name

    def execute(self, ecosystem, popular=True, count=None, nversions=None, force=False, recursive_limit=None,
                min_stars=None, max_stars=None, skip_if_exists=True, start_from=0):
        """Run analyses on the most-starred GitHub projects.

        :param ecosystem: ecosystem name
        :param popular: boolean, sort index by popularity
        :param count: int, number of projects to analyse
        :param nversions: how many (most popular) versions of each project to schedule
        :param force: force analyses scheduling
        :param recursive_limit: number of analyses done transitively
        :param min_stars: minimum number of GitHub stars
        :param max_stars: maximum number of GitHub stars
        :param skip_if_exists: do not process repositories for which results already exist
        :param start_from: int, skip first <number> most starred projects
        """
        self.count = int(count)
        self.ecosystem = ecosystem
        self.nversions = nversions
        self.force = force
        self.recursive_limit = recursive_limit
        self.min_stars = min_stars
        self.max_stars = max_stars
        self.skip_if_exists = skip_if_exists
        self.start_from = start_from or 0

        return self.do_execute()

    def do_execute(self):

        s3 = StoragePool.get_connected_storage('S3GitHubManifestMetadata')

        count = 0
        total_count = 0
        most_starred = self.get_most_starred_repositories(ecosystem=self.ecosystem, start_from=self.start_from)
        while count < self.count:
            try:
                repo_name = next(most_starred)
                total_count += 1
            except StopIteration:
                self.log.warning('No more repositories to process')
                break

            metadata_object_name = s3.get_object_key_path(self.ecosystem, repo_name) + '/metadata.json'
            if self.skip_if_exists and s3.object_exists(metadata_object_name):
                self.log.info('Results for repo %s already exist, skipping.', repo_name)
                count += 1  # skipped, but still counting
                continue

            repo_url = urllib.parse.urljoin(self.GITHUB_URL, repo_name + '.git')
            node_args = dict(
                ecosystem=self.ecosystem,
                force=self.force,
                repo_name=repo_name,
                url=repo_url
            )
            if self.recursive_limit is not None:
                node_args['recursive_limit'] = self.recursive_limit

            self.log.debug('Found most starred project number %s', total_count)
            self.run_selinon_flow('githubManifestMetadataFlow', node_args)
            count += 1
