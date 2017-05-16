import bs4
import requests
from .base import BaseHandler
try:
    import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib


class PythonPopularAnalyses(BaseHandler):
    """ Analyse top npm popular packages """

    _URL = 'http://pypi-ranking.info'
    _PACKAGES_PER_PAGE = 50
    _DEFAULT_COUNT = 1000

    @staticmethod
    def _parse_version_stats(html_version_stats):
        """ Parse version statistics from HTML definition and return ordered versions based on downloads

        :param html_version_stats: tr-like representation of version statistics
        :return: sorted versions based on downloads
        """
        result = []
        for version_definition in html_version_stats:
            # Access nested td
            version_name = version_definition.text.split('\n')[1]
            version_downloads = version_definition.text.split('\n')[4]
            # There are numbers with comma, get rid of it
            result.append((version_name, int(version_downloads.replace(',', ''))))

        return sorted(result, key=lambda x: x[1], reverse=True)

    def _use_pypi_xml_rpc(self, start, end, nversions, force=False, recursive_limit=None):
        """Schedule analyses of packages based on PyPI index using XML-RPC
        
        https://wiki.python.org/moin/PyPIXmlRpc
        
        :param start: starting index
        :param end: last package index to be analysed
        :param nversions: how many versions of each project to schedule
        :param force: force analyses scheduling
        :param recursive_limit: number of analyses done transitively
        """
        client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
        # get a list of package names
        packages = sorted(client.list_packages())

        for idx, package in enumerate(packages[start:end]):
            self.log.debug("Scheduling #%d. - %s", start + idx, package)
            releases = client.package_releases(package, True)  # True for show_hidden arg

            for version in releases[:nversions]:
                node_args = {
                    'ecosystem': 'pypi',
                    'name': package,
                    'version': version,
                    'force': force
                }
                if recursive_limit is not None:
                    node_args['recursive_limit'] = recursive_limit
                self.run_selinon_flow('bayesianFlow', node_args)

    def execute(self, popular=True, count=None, nversions=None, force=False, recursive_limit=None):
        """ Run bayesian core analyse on TOP Python packages

        :param popular: boolean, sort index by popularity
        :param count: str, number (or dash-separated range) of packages to analyse
        :param nversions: how many (most popular) versions of each project to schedule
        :param force: force analyses scheduling
        :param recursive_limit: number of analyses done transitively
        """
        _count = count or str(self._DEFAULT_COUNT)
        _count = sorted(map(int, _count.split("-")))
        if len(_count) == 1:
            _min = 0
            _max = _count[0]
        elif len(_count) == 2:
            _min = _count[0] - 1
            _max = _count[1]
        else:
            raise ValueError("Bad count %r" % count)

        to_schedule_count = _max - _min
        if to_schedule_count <= 0:
            raise ValueError("Bad count %r" % count)

        if not popular:
            self._use_pypi_xml_rpc(_min, _max, nversions, force, recursive_limit)
            return

        packages_count = 0
        page = int((_min / self._PACKAGES_PER_PAGE) + 1)
        page_offset = _min % self._PACKAGES_PER_PAGE

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

                pop = requests.get('{url}/module/{pkg}'.format(url=self._URL, pkg=package_name.text))
                poppage = bs4.BeautifulSoup(pop.text, 'html.parser')
                table = poppage.find('table', id='release_list')
                if table is None:
                    self.log.warning('No releases in %s', pop.url)
                    continue
                versions = self._parse_version_stats(table.find_all('tr'))

                self.log.debug("Scheduling #%d.", packages_count + _min)
                for version in versions[:nversions]:
                    node_args = {
                        'ecosystem': 'pypi',
                        'name': package_name.text,
                        'version': version[0],
                        'force': force
                    }

                    if recursive_limit is not None:
                        node_args['recursive_limit'] = recursive_limit
                    self.run_selinon_flow('bayesianFlow', node_args)
