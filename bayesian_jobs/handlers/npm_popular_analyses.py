import bs4
import requests
from .base import BaseHandler


class NpmPopularAnalyses(BaseHandler):
    """ Analyse top npm popular packages """

    _URL = 'https://www.npmjs.com/browse'
    _PACKAGES_PER_PAGE = 36
    _DEFAULT_COUNT = 1000

    def execute(self, count=None, nversions=None, force=False):
        """ Run bayesian core analyse on TOP npm packages

        :param count: number of packages to analyse
        :param nversions: how many (most popular) versions of each project to schedule
        :param force: force analyses scheduling
        """
        count = count or self._DEFAULT_COUNT
        scheduled = 0
        for offset in range(0, count, self._PACKAGES_PER_PAGE):
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
