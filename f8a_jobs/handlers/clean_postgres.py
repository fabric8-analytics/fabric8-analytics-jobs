from selinon import StoragePool
from sqlalchemy.exc import SQLAlchemyError
from f8a_worker.models import WorkerResult, Analysis, PackageAnalysis, PackageWorkerResult

from .base import BaseHandler


class CleanPostgres(BaseHandler):
    """Clean JSONB columns in Postgres."""

    def _clean_package_version_data(self, from_date, to_date, clean_unfinished):
        s3 = StoragePool.get_connected_storage('S3Data')

        query = self.postgres.session.query(WorkerResult).\
            join(Analysis). \
            filter(WorkerResult.external_request_id.is_(None)).\
            order_by(WorkerResult.id)

        if not clean_unfinished:
            query = query.filter(Analysis.finished_at.isnot(None))

        if from_date:
            query = query.filter(Analysis.started_at >= from_date)

        if to_date:
            query = query.filter(Analysis.finished_at <= to_date)

        start = 0
        while True:
            try:
                results = query.slice(start, start + 10).all()
            except SQLAlchemyError:
                self.postgres.session.rollback()
                raise

            if not results:
                self.log.info("Cleaning package-version data finished")
                break

            self.log.info("Updating results, slice offset is %s", start)
            start += 10

            for entry in results:
                if entry.worker[0].isupper() or \
                   entry.worker in ('recommendation', 'stack_aggregator'):
                    continue

                if not entry.task_result or 'version_id' in entry.task_result:
                    continue

                result_object_key = s3.construct_task_result_object_key(entry.ecosystem.name,
                                                                        entry.package.name,
                                                                        entry.version.identifier,
                                                                        entry.worker)

                if s3.object_exists(result_object_key):
                    entry.task_result = {'version_id': s3.retrieve_latest_version_id(
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

    def _clean_package_data(self, from_date, to_date, clean_unfinished):
        s3 = StoragePool.get_connected_storage('S3PackageData')

        query = self.postgres.session.query(PackageWorkerResult).\
            join(PackageAnalysis). \
            filter(PackageWorkerResult.external_request_id.is_(None)).\
            order_by(PackageWorkerResult.id)

        if not clean_unfinished:
            query = query.filter(PackageAnalysis.finished_at.isnot(None))

        if from_date:
            query = query.filter(PackageAnalysis.started_at >= from_date)

        if to_date:
            query = query.filter(PackageAnalysis.finished_at <= to_date)

        start = 0
        while True:
            try:
                results = query.slice(start, start + 10).all()
            except SQLAlchemyError:
                self.postgres.session.rollback()
                raise

            if not results:
                self.log.info("Cleaning package data finished")
                break

            self.log.info("Updating results, slice offset is %s", start)
            start += 10

            for entry in results:
                if entry.worker[0].isupper() or \
                   entry.worker in ('recommendation', 'stack_aggregator'):
                    continue

                if not entry.task_result or 'version_id' in entry.task_result:
                    continue

                result_object_key = s3.construct_task_result_object_key(entry.ecosystem.name,
                                                                        entry.package.name,
                                                                        entry.worker)

                if s3.object_exists(result_object_key):
                    entry.task_result = {'version_id': s3.retrieve_latest_version_id(
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

    def execute(self, from_date=None, to_date=None, clean_unfinished=False):
        if clean_unfinished:
            self.log.warning("Cleaning entries of unfinished analyses, this is DANGEROUS if some "
                             "analysis is in progress!!!")

        self.log.info("Cleaning computed data in package level flow")
        self._clean_package_data(from_date, to_date, clean_unfinished)
        self.log.info("Cleaning computed data in package level flows")
        self._clean_package_version_data(from_date, to_date, clean_unfinished)
        self.log.info("Cleaning has successfully finished")
