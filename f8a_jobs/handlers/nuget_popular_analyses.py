from bs4 import BeautifulSoup
from re import compile
from requests import get

from .base import AnalysesBaseHandler
from f8a_worker.solver import NugetReleasesFetcher


class NugetPopularAnalyses(AnalysesBaseHandler):
    """ Analyse popular nuget packages """

    _URL = 'https://www.nuget.org/packages?page={page}'
    _POPULAR_PACKAGES_PER_PAGE = 20

    def _scrape_nuget_org(self):
        """Schedule analyses for popular NuGet packages."""
        first_page = ((self.count.min-1) // self._POPULAR_PACKAGES_PER_PAGE) + 1
        last_page = ((self.count.max-1) // self._POPULAR_PACKAGES_PER_PAGE) + 1
        for page in range(first_page, last_page + 1):
            url = self._URL.format(page=page)
            pop = get(url)
            if not pop.ok:
                self.log.warning('Couldn\'t get url %r' % url)
                continue
            poppage = BeautifulSoup(pop.text, 'html.parser')
            packages = poppage.find_all('section', class_='package')
            if len(packages) == 0:
                # preview.nuget.org (will become nuget.org eventually) has a bit different structure
                packages = poppage.find_all('article', class_='package')
                if len(packages) == 0:
                    self.log.warning('Quitting, no packages on %r' % url)
                    break

            first_package = (self.count.min % self._POPULAR_PACKAGES_PER_PAGE) \
                if page == first_page else 1
            if first_package == 0:
                first_package = self._POPULAR_PACKAGES_PER_PAGE
            last_package = (self.count.max % self._POPULAR_PACKAGES_PER_PAGE) \
                if page == last_page else self._POPULAR_PACKAGES_PER_PAGE
            if last_package == 0:
                last_package = self._POPULAR_PACKAGES_PER_PAGE

            for package in packages[first_package-1:last_package]:
                # url_suffix ='/packages/ExtMongoMembership/1.7.0-beta'.split('/')
                url_suffix = package.find(href=compile(r'^/packages/'))['href'].split('/')
                if len(url_suffix) == 4:
                    name, releases = NugetReleasesFetcher(None).fetch_releases(url_suffix[2])
                    for release in releases[-self.nversions:]:
                        self.analyses_selinon_flow(name, release)

    def do_execute(self, popular=True):
        """Run analyses on NuGet packages.

        :param popular: boolean, sort index by popularity
        """
        if self.latest_version_only:
            self.nversions = 1
        # Use nuget.org for all (popular or not)
        self._scrape_nuget_org()
