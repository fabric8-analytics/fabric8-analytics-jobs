import requests
from .base import AnalysesBaseHandler


class GolangPopularAnalyses(AnalysesBaseHandler):
    """Schedule analyses for golang packages."""

    # API documentation: http://go-search.org/infoapi
    _URL = 'http://go-search.org/api'

    def _popular_packages(self):
        """Schedule analyses of popular packages in golang."""
        endpoint = self._URL + '?action=tops&len=100'

        response = requests.get(endpoint)
        response.raise_for_status()

        packages_seen = set()
        packages_seen_count = 0
        packages_scheduled = 0
        finished = False
        for top_category in response.json():
            if finished:
                break
            if top_category['Name'] == 'Sites':
                # This category does not list popular packages...
                continue
            self.log.info("Inspecting popular packages from category '%s'", top_category['Name'])
            for package in top_category['Items']:
                packages_seen_count += 1
                if package['Package'] in packages_seen:
                    self.log.debug("%s already seen" % package['Package'])
                    continue
                packages_seen.add(package['Package'])

                if packages_seen_count > self.count.max:
                    self.log.info("Scheduling of popular golang packages reached requested maximum")
                    finished = True  # to break the outer loop
                    break

                if packages_seen_count < self.count.min:
                    self.log.info("Skipping %d. entry '%s' - not in supplied range %s",
                                  packages_seen_count, package['Package'], self.count)

                # Use directly import path as a package name
                self.run_selinon_flow('bayesianPackageFlow', {
                    'ecosystem': self.ecosystem,
                    'name': package['Package'],
                    'url': package['Package'] or None,
                    'force': self.force
                })
                packages_scheduled += 1
            else:
                break

        self.log.info("Job has finished - scheduled analyses for %d most popular golang projects",
                      packages_scheduled)

    def _packages(self):
        """Schedule analyses of packages in golang (no sort criteria)."""
        endpoint = self._URL + '?action=packages'

        response = requests.get(endpoint)
        response.raise_for_status()

        packages_scheduled = 0
        for idx, import_path in enumerate(response.json()[self.count.min:self.count.max]):
            self.log.info("Package %d. in golang ecosystem '%s'", idx, import_path)
            self.run_selinon_flow('bayesianPackageFlow', {
                'ecosystem': self.ecosystem,
                'name': import_path,
                'url': import_path,
                'force': self.force
            })
            packages_scheduled += 1

        self.log.info("Job has finished - scheduled analyses for %d golang projects",
                      packages_scheduled)

    def do_execute(self, popular=True):
        """Run core analyse on golang packages.

        :param popular: boolean, sort packages by popularity
        """
        if self.nversions:
            self.log.warning("Version range provided, will be ignored for golang ecosystem "
                             "(no explicit versions available)")

        if popular:
            self._popular_packages()
        else:
            self._packages()
