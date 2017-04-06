import bs4
import requests
from .base import BaseHandler


class PythonPopularAnalyses(BaseHandler):
    """ Analyse top npm popular packages """

    _URL = 'http://pypi-ranking.info'
    _PACKAGES_PER_PAGE = 50
    _DEFAULT_COUNT = 1000

    def execute(self, count=None, nversions=None, force=False):
        """ Run bayesian core analyse on TOP Python packages

        :param count: str, number (or dash-separated range) of packages to analyse
        :param nversions: how many (most popular) versions of each project to schedule
        :param force: force analyses scheduling
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

        packages_count = 0
        page = int((_min / self._PACKAGES_PER_PAGE) + 1)
        page_offset = _min % self._PACKAGES_PER_PAGE

        while True:
            pop = requests.get('{url}/alltime?page={page}'.format(url=self._URL, page=page))
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
                for version_definition in poppage.find('table', id='release_list').find_all('tr')[:nversions]:
                    # Access nested td
                    version = version_definition.text.split('\n')[1]
                    self.run_selinon_flow('bayesianFlow', {
                        'ecosystem': 'python',
                        'name': package_name.text,
                        'version': version,
                        'force': force
                    })
