import datetime
from cucoslib.models import Analysis, Package, Version, Ecosystem
from cucoslib.workers import GraphImporterTask

from .base import BaseHandler


class SyncToGraph(BaseHandler):
    """ Sync all finished analyses to Graph DB """
    def execute(self):
        start = 0
        while True:
            results = self.postgres.session.query(Analysis).\
                join(Version).\
                join(Package).\
                join(Ecosystem).\
                filter(Analysis.finished_at != None).\
                slice(start, start + 100).all()

            if not results:
                self.log.info("Syncing to GraphDB finished")
                break

            self.log.info("Updating results, slice offset is %s", start)
            start += 100

            for entry in results:
                arguments = {'ecosystem': entry.version.package.ecosystem.name,
                             'name': entry.version.package.name,
                             'version': entry.version.identifier}
                GraphImporterTask.create_test_instance().execute(arguments)
                del entry
