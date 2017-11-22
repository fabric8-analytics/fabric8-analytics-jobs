import datetime
from selinon import StoragePool
from sqlalchemy.exc import SQLAlchemyError
from f8a_worker.models import WorkerResult, Analysis

from .base import BaseHandler


class CleanPostgres(BaseHandler):
    """Clean JSONB columns in Postgres."""

    def execute(self):
        s3 = StoragePool.get_connected_storage('S3Data')

        start = 0
        while True:
            try:
                results = self.postgres.session.query(WorkerResult).\
                    join(Analysis). \
                    filter(Analysis.started_at < datetime.datetime(2017, 4, 12, 7, 0, 0, 0)).\
                    filter(Analysis.finished_at.isnot(None)).\
                    filter(WorkerResult.external_request_id.is_(None)).\
                    order_by(WorkerResult.id).\
                    slice(start, start + 10).all()
            except SQLAlchemyError:
                self.postgres.session.rollback()
                raise

            if not results:
                self.log.info("Cleaning postgres finished")
                break

            self.log.info("Updating results, slice offset is %s", start)
            start += 10

            for entry in results:
                if entry.worker[0].isupper() or \
                   entry.worker in ('recommendation', 'stack_aggregator'):
                    continue

                if not entry.task_result or 'VersionId' in entry.task_result:
                    continue

                result_object_key = s3._construct_task_result_object_key(entry.ecosystem.name,
                                                                         entry.package.name,
                                                                         entry.version.identifier,
                                                                         entry.worker)

                if s3.object_exists(result_object_key):
                    entry.task_result = {'VersionId': s3.retrieve_latest_version_id(
                        result_object_key)}
                else:
                    entry.task_result = None
                    entry.error = True

                try:
                    self.postgres.session.commit()
                except SQLAlchemyError:
                    self.postgres.session.rollback()
                    raise

                del entry
