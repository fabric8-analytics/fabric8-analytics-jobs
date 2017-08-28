import datetime
from f8a_worker.models import Analysis, Package, Version, Ecosystem
from f8a_worker.workers import GraphImporterTask

from .base import BaseHandler


class SyncToGraph(BaseHandler):
    """ Sync all finished analyses to Graph DB """
    query_slice = 100

    def execute(self, start=0, end=0):
        base_query = self.postgres.session.query(Analysis).\
            join(Version).\
            join(Package).\
            join(Ecosystem).\
            filter(Analysis.finished_at.isnot(None)).\
            filter(Analysis.id >= start).\
            order_by(Analysis.id.asc())

        if end:
            base_query = base_query.filter(Analysis.id <= end)

        while True:
            self.log.info("Updating results, slice offset is %s", start)
            results = base_query.slice(start, start + self.query_slice).all()
            start += self.query_slice
            if not results:
                self.log.info("No more finished analyses => syncing to GraphDB finished")
                break

            for entry in results:
                arguments = {'ecosystem': entry.version.package.ecosystem.name,
                             'name': entry.version.package.name,
                             'version': entry.version.identifier}
                try:
                    self.log.info('Synchronizing {ecosystem}/{name}/{version} ...'.format(**arguments))
                    GraphImporterTask.create_test_instance().execute(arguments)
                except Exception as e:
                    self.log.exception('Failed to synchronize {ecosystem}/{name}/{version}'.
                                       format(**arguments))
                del entry
