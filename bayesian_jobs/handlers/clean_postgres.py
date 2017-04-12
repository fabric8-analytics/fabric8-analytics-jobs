from selinon import StoragePool
from cucoslib.models import WorkerResult, Analysis

from .base import BaseHandler


class CleanPostgres(BaseHandler):
    """ Clean JSONB columns in Postgres """
    def execute(self):
        s3 = StoragePool.get_connected_storage('S3Data')

        results = self.postgres.session.query(WorkerResult).join(Analysis).\
            filter(Analysis.finished_at != None).\
            filter(WorkerResult.external_request_id == None)

        for entry in results:
            if entry.worker[0].isupper() or entry.worker in ('recommendation', 'stack_aggregator'):
                continue

            if 'VersionId' in entry.task_result:
                continue

            result_object_key = s3._construct_task_result_object_key(entry.ecosystem.name,
                                                                     entry.package.name,
                                                                     entry.version.identifier,
                                                                     entry.worker)

            if s3.object_exists(result_object_key):
                entry.task_result = {'VersionId': s3.retrieve_latest_version_id(result_object_key)}
            else:
                entry.task_result = None
                entry.error = True

            self.postgres.session.commit()
