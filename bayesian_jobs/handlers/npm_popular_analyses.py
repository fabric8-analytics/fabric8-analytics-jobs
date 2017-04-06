import bs4
import requests
from .base import BaseHandler


class NpmPopularAnalyses(BaseHandler):
    """ Analyse top npm popular packages """

    _URL = 'https://www.npmjs.com/browse'
    _PACKAGES_PER_PAGE = 36
    _DEFAULT_COUNT = 1000

    def execute(self, popular=True, count=None, nversions=None, force=False):
        """ Run bayesian core analyse on TOP npm packages

        :param popular: boolean, sort index by popularity
        :param count: str, number (or dash-separated range) of packages to analyse
        :param nversions: how many (most popular) versions of each project to schedule
        :param force: force analyses scheduling
        """
        if not popular:
            self.log.warning("Not sorting by popularity has not been implemented yet. "
                             "Will sort by popularity anyway.")

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

        count = count or self._DEFAULT_COUNT
        scheduled = 0
        for offset in range(_min, _max, self._PACKAGES_PER_PAGE):
            pop = requests.get('{url}/star?offset={offset}'.format(url=self._URL, offset=offset))
            poppage = bs4.BeautifulSoup(pop.text, 'html.parser')
            for link in poppage.find_all('a', class_='version'):
                node_args = {
                    'ecosystem': 'npm',
                    'name': link.get('href')[len('/package/'):],
                    # TODO: get and schedule nversions
                    'version': link.text,
                    'force': force
                }
                self.run_selinon_flow('bayesianFlow', node_args)
                scheduled += 1
                if scheduled == count:
                    return
