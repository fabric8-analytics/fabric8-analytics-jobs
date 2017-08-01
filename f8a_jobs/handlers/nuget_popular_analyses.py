from bs4 import BeautifulSoup
from re import search
from requests import get

from .base import AnalysesBaseHandler, CountRange


class NugetPopularAnalyses(AnalysesBaseHandler):
    """ Analyse popular nuget packages """

    _URL = 'https://libraries.io/search?order=desc&page={page}&platforms=NuGet&sort=rank'
    _POPULAR_PACKAGES_PER_PAGE = 30
    _MAX_PAGES = 100  # pages higher than this return 404
    _MAX_PACKAGES = _POPULAR_PACKAGES_PER_PAGE * _MAX_PAGES

    def _use_libraries_io(self):
        """Schedule analyses for popular NuGet packages."""
        first_page = ((self.count.min-1) // self._POPULAR_PACKAGES_PER_PAGE) + 1
        if self.count.max > self._MAX_PACKAGES:
            self.count = CountRange(self.count.min, self._MAX_PACKAGES)
            self.log.warning("Libraries.io provides only first %d most popular packages" %
                             self._MAX_PACKAGES)
        last_page = ((self.count.max-1) // self._POPULAR_PACKAGES_PER_PAGE) + 1
        for page in range(first_page, last_page + 1):
            url = self._URL.format(page=page)
            pop = get(url)
            if not pop.ok:
                self.log.warning('Couldn\'t get url %r' % url)
                continue
            poppage = BeautifulSoup(pop.text, 'html.parser')
            projects = poppage.find_all('div', class_='project')
            if len(projects) == self._POPULAR_PACKAGES_PER_PAGE:
                first_package = (self.count.min % self._POPULAR_PACKAGES_PER_PAGE) \
                    if page == first_page else 1
                if first_package == 0:
                    first_package = self._POPULAR_PACKAGES_PER_PAGE
                last_package = (self.count.max % self._POPULAR_PACKAGES_PER_PAGE) \
                    if page == last_page else self._POPULAR_PACKAGES_PER_PAGE
                if last_package == 0:
                    last_package = self._POPULAR_PACKAGES_PER_PAGE
                projects = projects[first_package-1:last_package]
            else:
                # Don't do any slicing here
                self.log.warning('%r contains different number of packages than expected %d' %
                                 (url, self._POPULAR_PACKAGES_PER_PAGE))

            for project in projects:
                # <div class="project" style="border-color: #178600;">
                # <h5>
                # <a href="/nuget/Newtonsoft.Json">Newtonsoft.Json</a>
                # </h5>
                # <div class="">
                # Json.NET is a popular high-performance JSON framework for .NET
                # </div>
                # <small>
                # Latest release 10.0.3 -
                # Updated
                # <time data-time-ago="2017-06-18T02:10:29+00:00" datetime="2017-06-18T02:10:29+00:00" title="Jun 18, 2017">about 1 month ago</time>
                # - 4.42K stars
                # </small>
                # </div>
                package = project.find('a').text
                version = search(r'\nLatest release (.+) -\n', project.text).group(1)
                self.analyses_selinon_flow(package, version)

    def do_execute(self, popular=True):
        """Run analyses on NuGet packages.

        :param popular: boolean, sort index by popularity
        """

        # Use libraries.io for all (popular or not)
        self._use_libraries_io()
