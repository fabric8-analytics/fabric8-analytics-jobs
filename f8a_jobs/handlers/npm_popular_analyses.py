import json
import bs4
import requests
from .base import AnalysesBaseHandler


class NpmPopularAnalyses(AnalysesBaseHandler):
    """ Analyse top npm popular packages """

    _URL_REGISTRY = 'https://skimdb.npmjs.com/registry/'
    _URL_POPULAR = 'https://www.npmjs.com/browse'
    _POPULAR_PACKAGES_PER_PAGE = 36

    def _schedule_from_npm_registry(self, package, offset):
        """Schedule analyses of specific versions using skimdb.npmjs.com API"""
        package_info = requests.get(self._URL_REGISTRY + package).json()

        if self.nversions == 1:
            self.log.debug("Scheduling #%d. (latest version)", self.count.min + offset)
            latest = package_info.get('dist-tags', {}).get('latest', None)
            if latest:
                self.analyses_selinon_flow(package, latest)
            else:
                self.log.debug("latest version for %d not found - probably has no releases",
                               package)
        else:
            self.log.debug("Scheduling #%d. (number versions: %d)",
                           self.count.min + offset, self.nversions)
            for version in sorted(package_info.get('versions', {}).keys(),
                                  reverse=True)[:self.nversions]:
                self.analyses_selinon_flow(package, version)

    def _use_npm_registry(self):
        """Schedule analyses for popular NPM packages."""
        # set offset to -2 so we skip the very first line
        offset = -2
        stream = requests.get(self._URL_REGISTRY + '_all_docs?skip={}&limit={}'
                              .format(self.count.min, self.count.max - self.count.min), stream=True)
        stream.raise_for_status()

        # this solution might be ugly, but is quiet efficient compared to downloading info
        # from https://registry.npmjs.org/-/all that has 270MB+
        try:
            for record in stream.iter_lines():
                offset += 1

                if offset < 0:
                    # skip header
                    continue

                # hack - remove comma from entries that need it so we can directly parse valid JSON
                record = record.decode()
                if record.endswith(','):
                    record = record[:-1]
                if record == ']}':
                    self.log.debug("No more entries to schedule, exiting")
                    break

                record = json.loads(record)
                self._schedule_from_npm_registry(record['key'], offset)
        finally:
            stream.close()

    def _use_npm_popular(self):
        """Schedule analyses for popular NPM packages."""
        scheduled = 0
        count = self.count.max - self.count.min + 1
        for offset in range(self.count.min - 1, self.count.max, self._POPULAR_PACKAGES_PER_PAGE):
            pop = requests.get('{url}/depended?offset={offset}'.format(url=self._URL_POPULAR,
                                                                       offset=offset))
            poppage = bs4.BeautifulSoup(pop.text, 'html.parser')
            for link in poppage.find_all('a', class_='type-neutral-1'):
                self._schedule_from_npm_registry(link.get('href')[len('/package/'):], scheduled)
                scheduled += 1
                if scheduled == count:
                    return

    def do_execute(self, popular=True):
        """Run analyses on NPM packages.

        :param popular: boolean, sort index by popularity
        """
        if popular:
            self._use_npm_popular()
        else:
            self._use_npm_registry()
