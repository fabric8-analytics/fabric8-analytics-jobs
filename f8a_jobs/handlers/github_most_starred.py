import requests
import urllib.parse
from .base import AnalysesBaseHandler


class GitHubMostStarred(AnalysesBaseHandler):
    """ Store metadata of most starred <insert-your-favourite-ecosystem> projects
    on GitHub to an S3 bucket. """

    GITHUB_API_URL = 'https://api.github.com/'
    GITHUB_URL = 'https://github.com/'

    # ecosystem->(GitHub-language, supported-manifest) mapping
    _ECOSYSTEM_DETAILS = {'maven': ('java', 'pom.xml'),
                          'npm': ('javascript', 'package.json'),
                          'pypi': ('python', 'requirements.txt')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_stars = 0

    def get_most_starred_repositories(self, ecosystem, min_stars):
        url_path = 'search/repositories?q=language:{lang}+stars:>={stars}+sort:stars&page={page}'
        url_template = urllib.parse.urljoin(self.GITHUB_API_URL, url_path)

        page = 1
        repos = []

        def get(lang, page_number):
            url = url_template.format(lang=lang, stars=min_stars, page=page_number)
            response = requests.get(url)
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
                force_graph_sync=False, min_stars=0):
        super().execute(ecosystem, popular=True, count=None, nversions=None, force=False, recursive_limit=None,
                        force_graph_sync=False)
        self.min_stars = min_stars

    def do_execute(self, popular=True):
        """
        :param popular: bool, not needed, not used
        """

        count = 0
        most_starred = self.get_most_starred_repositories(ecosystem=self.ecosystem, min_stars=self.min_stars)
        while count < self.count.max:
            try:
                repo_name = next(most_starred)
            except StopIteration:
                self.log.warning('No more repositories to process')
                break
            repo_url = urllib.parse.urljoin(self.GITHUB_URL, repo_name + '.git')
            node_args = dict(
                ecosystem=self.ecosystem,
                force=self.force,
                repo_name=repo_name,
                url=repo_url
            )
            if self.recursive_limit is not None:
                node_args['recursive_limit'] = self.recursive_limit

            self.run_selinon_flow('githubManifestMetadataFlow', node_args)
            count += 1
