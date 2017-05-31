import bs4
from collections import OrderedDict
import os
import re
import requests
from selinon import StoragePool

from .base import AnalysesBaseHandler
from cucoslib.utils import cwd, TimedCommand


class MavenPopularAnalyses(AnalysesBaseHandler):
    """ Analyse top maven popular projects """

    _BASE_URL = 'http://mvnrepository.com'
    _MAX_PAGES = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.projects = OrderedDict()
        self.nprojects = 0

    @staticmethod
    def _find_versions(project_page):
        def _has_numeric_usages(tag):
            return tag.has_attr('href') and \
                   tag.get('href').endswith('/usages') and \
                   tag.get_text().replace(',', '').isnumeric()
        usage_tags = project_page.find_all(_has_numeric_usages)
        if usage_tags:
            # sort according to usage
            usage_tags = sorted(usage_tags, key=lambda u: int(u.text.replace(',', '')), reverse=True)
            # [<a href="jboss-logging-log4j/2.0.5.GA/usages">64</a>]
            versions = [v.get('href').split('/')[-2] for v in usage_tags]
        else:  # no usage stats, get the versions other way
            versions = project_page.find_all('a', class_=re.compile('vbtn *'))
            # [<a class="vbtn release" href="common-angularjs/3.8">3.8</a>]
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
        for page in range(1, self._MAX_PAGES+1):
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
                all_versions = self._find_versions(artpage)
                if name not in self.projects and all_versions:
                    versions = all_versions[:self.nversions]
                    self.projects[name] = versions
                    self.log.debug("Scheduling #%d. (number versions: %d)", self.nprojects, self.nversions)
                    self.nprojects += 1
                    for version in versions:
                        # TODO: this can be unrolled
                        if self.count.min <= self.nprojects <= self.count.max:
                            self.analyses_selinon_flow(name, version)
                        else:
                            self.log.debug("Skipping scheduling for #%d. (min=%d, max=%d, name=%s, version=%s)",
                                           self.nprojects, self.count.min, self.count.max, name, version)

                    if self.nprojects >= self.count.max:
                        return

    def _top_projects(self):
        """ Scrape Top Projects page @ http://mvnrepository.com/popular """
        self.log.debug('Scraping Top Projects page http://mvnrepository.com/popular')
        self._projects_from('/popular')

    def _top_categories_projects(self):
        """ Scrape Top Categories page @ http://mvnrepository.com/open-source """
        for page in range(1, self._MAX_PAGES+1):
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
        """ Scrape Popular Tags page @ http://mvnrepository.com/tags """
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
        target_dir = os.path.join(maven_index_checker_dir, 'target')

        s3 = StoragePool.get_connected_storage('S3MavenIndex')
        self.log.info('Fetching pre-built maven index from S3, if available.')
        s3.retrieve_index_if_exists(target_dir)

        index_range = '{}-{}'.format(self.count.min, self.count.max)
        command = ['java', '-Xmx768m', '-jar', 'maven-index-checker.jar', '-r', index_range]
        with cwd(maven_index_checker_dir):
            output = TimedCommand.get_command_output(command, is_json=True, graceful=False)
            for idx, release in enumerate(output):
                name = '{}:{}'.format(release['artifactId'], release['groupId'])
                version = release['version']
                self.log.debug("Scheduling #%d.", self.count.min + idx)
                self.analyses_selinon_flow(name, version)

        s3.store_index(target_dir)

    def do_execute(self, popular=True):
        """Run bayesian core analyse on maven projects.

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
