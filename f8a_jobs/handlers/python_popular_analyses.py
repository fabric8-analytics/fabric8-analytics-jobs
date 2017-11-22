import bs4
import requests
from .base import AnalysesBaseHandler
try:
    import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib


class PythonPopularAnalyses(AnalysesBaseHandler):
    """Analyse top npm popular packages."""

    _URL = 'http://pypi-ranking.info'
    _PACKAGES_PER_PAGE = 50

    @staticmethod
    def _parse_version_stats(html_version_stats, sort_by_popularity=True):
        """Parse version statistics from HTML definition.

        Parse version statistics from HTML definition and return ordered
        versions based on downloads

        :param html_version_stats: tr-like representation of version statistics
        :param sort_by_popularity: whether or not to return versions sorted by popularity
        :return: sorted versions based on downloads
        """
        result = []
        for version_definition in html_version_stats:
            # Access nested td
            version_name = version_definition.text.split('\n')[1]
            version_downloads = version_definition.text.split('\n')[4]
            # There are numbers with comma, get rid of it
            result.append((version_name, int(version_downloads.replace(',', ''))))

        if sort_by_popularity:
            return sorted(result, key=lambda x: x[1], reverse=True)
        return result

    def _use_pypi_xml_rpc(self):
        """Schedule analyses of packages based on PyPI index using XML-RPC.

        https://wiki.python.org/moin/PyPIXmlRpc
        """
        client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
        # get a list of package names
        packages = sorted(client.list_packages())

        for idx, package in enumerate(packages[self.count.min:self.count.max]):
            releases = client.package_releases(package, True)  # True for show_hidden arg

            self.log.debug("Scheduling #%d. (number versions: %d)",
                           self.count.min + idx, self.nversions)
            for version in releases[:self.nversions]:
                self.analyses_selinon_flow(package, version)

    def _use_pypi_ranking(self):
        """Schedule analyses of packages based on PyPI ranking."""
        to_schedule_count = self.count.max - self.count.min
        packages_count = 0
        page = int((self.count.min / self._PACKAGES_PER_PAGE) + 1)
        page_offset = self.count.min % self._PACKAGES_PER_PAGE

        while True:
            pop = requests.get('{url}/alltime?page={page}'.format(url=self._URL, page=page))
            pop.raise_for_status()

            poppage = bs4.BeautifulSoup(pop.text, 'html.parser')
            page += 1

            for package_name in poppage.find_all('span', class_='list_title'):
                if page_offset:
                    page_offset -= 1
                    continue

                packages_count += 1
                if packages_count > to_schedule_count:
                    return

                pop = requests.get('{url}/module/{pkg}'.format(url=self._URL,
                                                               pkg=package_name.text))
                poppage = bs4.BeautifulSoup(pop.text, 'html.parser')
                table = poppage.find('table', id='release_list')
                if table is None:
                    self.log.warning('No releases in %s', pop.url)
                    continue
                versions = self._parse_version_stats(table.find_all('tr'),
                                                     sort_by_popularity=self.nversions > 1)

                self.log.debug("Scheduling #%d. (number versions: %d)",
                               self.count.min + packages_count, self.nversions)
                for version in versions[:self.nversions]:
                    self.analyses_selinon_flow(package_name.text, version[0])

    def do_execute(self, popular=True):
        """Run core analyse on Python packages.

        :param popular: boolean, sort index by popularity
        """
        if popular:
            self._use_pypi_ranking()
        else:
            self._use_pypi_xml_rpc()
