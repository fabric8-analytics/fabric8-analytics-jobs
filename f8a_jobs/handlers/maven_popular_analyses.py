import bs4
from collections import OrderedDict
import os
import re
import requests
import tempfile
from selinon import StoragePool
from shutil import rmtree

from .base import AnalysesBaseHandler
from f8a_worker.utils import cwd, TimedCommand
from f8a_worker.errors import TaskError


class MavenPopularAnalyses(AnalysesBaseHandler):
    """Analyse top maven popular projects."""

    _BASE_URL = 'http://mvnrepository.com'
    _MAX_PAGES = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.projects = OrderedDict()
        self.nprojects = 0

    @staticmethod
    def _find_versions(project_page, latest_version_only=False):
        def _has_numeric_usages(tag):
            return tag.has_attr('href') and \
                   tag.get('href').endswith('/usages') and \
                   tag.get_text().replace(',', '').isnumeric()
        usage_tags = project_page.find_all(_has_numeric_usages)
        if usage_tags and not latest_version_only:
            # sort according to usage
            usage_tags = sorted(usage_tags, key=lambda u: int(u.text.replace(',', '')),
                                reverse=True)
            # [<a href="jboss-logging-log4j/2.0.5.GA/usages">64</a>]
            versions = [v.get('href').split('/')[-2] for v in usage_tags]
        else:  # no usage stats, get the versions other way
            versions = project_page.find_all('a', class_=re.compile('vbtn *'))
            # [<a class="vbtn release" href="common-angularjs/3.8">3.8</a>]
            if latest_version_only:
                # take the first one (always the latest version)
                versions = versions[:1]
            else:
                versions = sorted(versions, key=lambda v: v.text, reverse=True)
            versions = [v.text for v in versions]
        return versions

    def _projects_from(self, url_suffix):
        """

        :param url_suffix: to add to _BASE_URL
        :return: 2-tuple of (dict of {project_name: [versions]}, number of found projects)
        """
        if not url_suffix.startswith('/'):
            url_suffix = '/' + url_suffix
        for page in range(1, self._MAX_PAGES + 1):
            page_link = '{base_url}{url_suffix}?p={page}'.format(base_url=self._BASE_URL,
                                                                 url_suffix=url_suffix,
                                                                 page=page)
            pop = requests.get(page_link)
            poppage = bs4.BeautifulSoup(pop.text, 'html.parser')
            for link in poppage.find_all('a', class_='im-usage'):
                # <a class="im-usage" href="/artifact/junit/junit/usages"><b>56,752</b> usages</a>
                artifact = link.get('href')[0:-len('/usages')]
                artifact_link = '{url}{a}'.format(url=self._BASE_URL, a=artifact)
                art = requests.get(artifact_link)
                artpage = bs4.BeautifulSoup(art.text, 'html.parser')
                name = artifact[len('/artifact/'):].replace('/', ':')
                all_versions = self._find_versions(artpage, self.nversions == 1)
                if name not in self.projects and all_versions:
                    versions = all_versions[:self.nversions]
                    self.log.debug("Scheduling #%d. (number versions: %d)",
                                   self.nprojects, self.nversions)
                    self.projects[name] = versions
                    self.nprojects += 1
                    for version in versions:
                        # TODO: this can be unrolled
                        if self.count.min <= self.nprojects <= self.count.max:
                            self.analyses_selinon_flow(name, version)
                        else:
                            self.log.debug("Skipping scheduling for #%d. (min=%d, max=%d, "
                                           "name=%s, version=%s)",
                                           self.nprojects, self.count.min, self.count.max, name,
                                           version)

                    if self.nprojects >= self.count.max:
                        return

    def _top_projects(self):
        """Scrape Top Projects page @ http://mvnrepository.com/popular."""
        self.log.debug('Scraping Top Projects page http://mvnrepository.com/popular')
        self._projects_from('/popular')

    def _top_categories_projects(self):
        """Scrape Top Categories page @ http://mvnrepository.com/open-source."""
        for page in range(1, self._MAX_PAGES + 1):
            page_link = '{url}/open-source?p={page}'.format(url=self._BASE_URL, page=page)
            self.log.debug('Scraping Top Categories page %s' % page_link)
            cat = requests.get(page_link)
            catpage = bs4.BeautifulSoup(cat.text, 'html.parser')
            # [<a href="/open-source/testing-frameworks">more...</a>]
            for link in catpage.find_all('a', text='more...'):
                category = link.get('href')
                self._projects_from(category)
                if self.nprojects >= self.count.max:
                    return

    def _top_tags_projects(self):
        """Scrape Popular Tags page @ http://mvnrepository.com/tags."""
        page_link = '{url}/tags'.format(url=self._BASE_URL)
        self.log.debug('Scraping Popular Tags page %s' % page_link)
        tags_page = requests.get(page_link)
        tagspage = bs4.BeautifulSoup(tags_page.text, 'html.parser')
        tags_a = tagspage.find_all('a', class_=re.compile('t[1-9]'))
        # [<a class="t4" href="/tags/accumulo">accumulo</a>,
        #  <a class="t7" href="/tags/actor">actor</a>]
        tags_a = sorted(tags_a, key=lambda x: x.get('class'), reverse=True)
        for link in tags_a:
            tag = link.get('href')
            self._projects_from(tag)
            if self.nprojects >= self.count.max:
                return

    def _use_maven_index_checker(self):
        maven_index_checker_dir = os.getenv('MAVEN_INDEX_CHECKER_PATH')
        maven_index_checker_data_dir = os.environ.get('MAVEN_INDEX_CHECKER_DATA_PATH',
                                                      '/tmp/index-checker')
        os.makedirs(maven_index_checker_data_dir, exist_ok=True)
        central_index_dir = os.path.join(maven_index_checker_data_dir, 'central-index')
        timestamp_path = os.path.join(central_index_dir, 'timestamp')

        s3 = StoragePool.get_connected_storage('S3MavenIndex')
        self.log.info('Fetching pre-built maven index from S3, if available.')
        s3.retrieve_index_if_exists(maven_index_checker_data_dir)

        old_timestamp = 0
        try:
            old_timestamp = int(os.stat(timestamp_path).st_mtime)
        except OSError:
            self.log.info('Timestamp is missing, we will probably need to build the index '
                          'from scratch.')
            pass

        java_temp_dir = tempfile.mkdtemp(prefix='tmp-', dir=os.environ.get('PV_DIR', '/tmp'))

        index_range = '{}-{}'.format(self.count.min, self.count.max)
        command = ['java', '-Xmx768m',
                   '-Djava.io.tmpdir={}'.format(java_temp_dir),
                   '-DcentralIndexDir={}'.format(central_index_dir),
                   '-jar', 'maven-index-checker.jar', '-r', index_range]
        if self.nversions == 1:
            command.append('-l')
        with cwd(maven_index_checker_dir):
            try:
                output = TimedCommand.get_command_output(command, is_json=True, graceful=False,
                                                         timeout=1200)

                new_timestamp = int(os.stat(timestamp_path).st_mtime)
                if old_timestamp != new_timestamp:
                    self.log.info('Storing pre-built maven index to S3...')
                    s3.store_index(maven_index_checker_data_dir)
                    self.log.debug('Stored. Index in S3 is up-to-date.')
                else:
                    self.log.info('Index in S3 is up-to-date.')
            except TaskError as e:
                self.log.exception(e)
                raise
            finally:
                rmtree(central_index_dir)
                self.log.debug('central-index/ deleted')
                rmtree(java_temp_dir)

            s3data = StoragePool.get_connected_storage('S3Data')
            bucket = s3data._s3.Bucket(s3data.bucket_name)
            for idx, release in enumerate(output):
                name = '{}:{}'.format(release['groupId'], release['artifactId'])
                version = release['version']
                # For now (can change in future) we want to analyze only ONE version of each package
                try:
                    next(iter(bucket.objects.filter(Prefix='{e}/{p}/'.format(
                        e=self.ecosystem, p=name)).limit(1)))
                    self.log.info("Analysis of some version of %s has already been scheduled, "
                                  "skipping version %s", name, version)
                    continue
                except StopIteration:
                    self.log.info("Scheduling #%d.", self.count.min + idx)
                    self.analyses_selinon_flow(name, version)

    def do_execute(self, popular=True):
        """Run core analyse on maven projects.

        :param popular: boolean, sort index by popularity
        """
        if popular:
            self._top_projects()

            if self.nprojects < self.count.max:
                # There's only 100 projects on Top Projects page, look at top categories
                self._top_categories_projects()

            if self.nprojects < self.count.max:
                # Still not enough ? Ok, let's try popular tags
                self._top_tags_projects()

            if self.nprojects < self.count.max:
                self.log.warning("No more sources of popular projects. "
                                 "%d will be scheduled instead of requested %d" % (self.nprojects,
                                                                                   self.count.max))
        else:
            self._use_maven_index_checker()
