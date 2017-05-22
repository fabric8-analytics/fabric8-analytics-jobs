import json
import bs4
import requests
from .base import BaseHandler


class NpmPopularAnalyses(BaseHandler):
    """ Analyse top npm popular packages """

    _URL_REGISTRY = 'https://skimdb.npmjs.com/registry/'
    _URL_POPULAR = 'https://www.npmjs.com/browse'
    _POPULAR_PACKAGES_PER_PAGE = 36
    _DEFAULT_COUNT = 1000

    def _use_npm_registry(self, start, stop, nversions, force, recursive_limit, force_graph_sync=False):
        """Schedule analyses for popular NPM packages

        :param start: start offset for popular projects
        :param stop: stop offset for popular projects
        :param nversions: how many of each project to schedule
        :param force: force analyses scheduling
        :param recursive_limit: number of analyses done transitively
        :param force_graph_sync: force graph synchronization if already analysed
        """
        # set offset to -2 so we skip the very first line
        offset = -2
        stream = requests.get(self._URL_REGISTRY + '_all_docs?skip={}&limit={}'.format(start, stop-start), stream=True)
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
                self.log.debug(record)
                if record.endswith(','):
                    record = record[:-1]
                if record == ']}':
                    self.log.debug("No more entries to schedule, exiting")
                    break

                record = json.loads(record)
                package_info = requests.get(self._URL_REGISTRY + record['key']).json()
                for version in sorted(package_info['versions'].keys(), reverse=True)[:nversions]:
                    node_args = {
                        'ecosystem': 'npm',
                        'name': record['key'],
                        'version': version,
                        'force': force,
                        'force_graph_sync': force_graph_sync
                    }
                    if recursive_limit is not None:
                        node_args['recursive_limit'] = recursive_limit
                    self.run_selinon_flow('bayesianFlow', node_args)
        finally:
            stream.close()

    def _use_npm_popular(self, start, stop, nversions, force, recursive_limit, force_graph_sync=False):
        """Schedule analyses for popular NPM packages

        :param start: start offset for popular projects
        :param stop: stop offset for popular projects
        :param nversions: how many most popular versions of each project to schedule
        :param force: force analyses scheduling
        :param recursive_limit: number of analyses done transitively
        :param force_graph_sync: force graph synchronization if already analysed
        """
        scheduled = 0
        count = stop - start
        for offset in range(start, stop, self._POPULAR_PACKAGES_PER_PAGE):
            pop = requests.get('{url}/star?offset={offset}'.format(url=self._URL_POPULAR, offset=offset))
            poppage = bs4.BeautifulSoup(pop.text, 'html.parser')
            for link in poppage.find_all('a', class_='version'):
                self.log.debug("Scheduling #%d.", offset)
                node_args = {
                    'ecosystem': 'npm',
                    'name': link.get('href')[len('/package/'):],
                    # TODO: get and schedule nversions
                    'version': link.text,
                    'force': force,
                    'force_graph_sync': force_graph_sync
                }

                if recursive_limit is not None:
                    node_args['recursive_limit'] = recursive_limit
                self.run_selinon_flow('bayesianFlow', node_args)

                scheduled += 1
                if scheduled == count:
                    return

    def execute(self, popular=True, count=None, nversions=None, force=False, recursive_limit=None,
                force_graph_sync=False):
        """Run analyses on NPM packages

        :param popular: boolean, sort index by popularity
        :param count: str, number (or dash-separated range) of packages to analyse
        :param nversions: how many versions of each project to schedule
        :param force: force analyses scheduling
        :param recursive_limit: number of analyses done transitively
        :param force_graph_sync: force graph synchronization if already analysed
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

        if popular:
            self._use_npm_popular(_min, _max, nversions, force, recursive_limit, force_graph_sync)
        else:
            self._use_npm_registry(_min, _max, nversions, force, recursive_limit, force_graph_sync)
