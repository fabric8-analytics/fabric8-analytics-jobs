from dateutil.parser import parse as parse_datetime
from selinon import StoragePool
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from f8a_worker.models import WorkerResult, Analysis, Ecosystem, Package, Version

from .base import BaseHandler


class AggregateTopics(BaseHandler):
    """Aggregate gathered topics and store them on S3."""

    def _store_topics(self, bucket_name, object_key, report):
        self.log.info("Storing aggregated topics on S3")
        s3_destination = StoragePool.get_connected_storage('AmazonS3')

        # hack for temporary change bucket name so we have everything set up
        old_bucket_name = s3_destination.bucket_name
        try:
            s3_destination.bucket_name = bucket_name
            s3_destination.store_dict(report, object_key)
        finally:
            s3_destination.bucket_name = old_bucket_name

    def execute(self, ecosystem, bucket_name, object_key, from_date=None, to_date=None):
        """Aggregate gathered topics and store them on S3.

        :param ecosystem: ecosystem name for which topics should be gathered
        :param bucket_name: name of the destination bucket to which topics should be stored
        :param object_key: name of the object under which aggregated topics should be stored
        :param from_date: date limitation for task result queries
        :param to_date: date limitation for taks result queries
        """
        if from_date is not None:
            from_date = parse_datetime(from_date)
        if to_date is not None:
            to_date = parse_datetime(to_date)

        s3 = StoragePool.get_connected_storage('S3Data')
        postgres = StoragePool.get_connected_storage('PackagePostgres')

        base_query = postgres.session.query(WorkerResult).\
            join(Analysis). \
            join(Version).\
            join(Package).\
            join(Ecosystem).\
            filter(WorkerResult.error.is_(False)).\
            filter(WorkerResult.worker == 'github_details').\
            filter(Ecosystem.name == ecosystem)

        if from_date is not None:
            base_query = base_query.filter(Analysis.started_at > from_date).\
                order_by(desc(WorkerResult.id))

        if to_date is not None:
            base_query = base_query.filter(Analysis.started_at < to_date).\
                order_by(desc(WorkerResult.id))

        start = 0
        topics = []
        while True:
            try:
                results = base_query.slice(start, start + 10).all()
            except SQLAlchemyError:
                postgres.session.rollback()
                raise

            if not results:
                break

            self.log.info("Collecting topics, slice offset is %s", start)
            start += 10

            for entry in results:
                name = entry.package.name
                version = entry.version.identifier

                self.log.debug("Aggregating topics for %s/%s/%s", ecosystem, name, version)

                task_result = entry.task_result
                if not postgres.is_real_task_result(task_result):
                    self.log.debug("Result was already stored on S3, retrieving from there")
                    try:
                        task_result = s3.retrieve_task_result(ecosystem, name, version,
                                                              'github_details')
                    except:
                        self.log.exception("Failed to retrieve result 'github_details' from S3 "
                                           "for %s/%s/%s", ecosystem, name, version)
                        continue

                topics.append({
                    'topics': task_result.get('details', {}).get('topics'),
                    'name': name,
                    'ecosystem': ecosystem,
                    'version': version
                })

        report = {
            'ecosystem': ecosystem,
            'bucket_name': bucket_name,
            'object_key': object_key,
            'from_date': str(from_date),
            'to_date': str(to_date),
            'result': topics
        }
        self._store_topics(bucket_name, object_key, report)
