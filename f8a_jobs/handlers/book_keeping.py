"""Class to retrieve BookKeeping data."""

from selinon import StoragePool
from f8a_worker.models import (Analysis, Ecosystem, Package, Version,
                               WorkerResult, PackageWorkerResult, PackageAnalysis)
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import SQLAlchemyError


class BookKeeping(object):
    """Class to retrieve BookKeeping data."""
    def __init__(self):
        """Initialize instance."""
        rdb = StoragePool.get_connected_storage('BayesianPostgres')
        self.db = rdb.session

    def retrieve_bookkeeping_all(self):
        """Retrieve BookKeeping data for all Ecosystems."""
        try:
            data = []
            for e in self.db.query(Ecosystem).all():
                package_count = self.db.query(Package).filter(Package.ecosystem == e).count()
                ecosystem_name = self.db.query(Ecosystem).get(e.id).name
                pv_count = self.db.query(Version).join(Package).\
                    filter(Package.ecosystem == e).count()
                entry = {
                    "name": ecosystem_name,
                    "package_count": package_count,
                    "package_version_count": pv_count
                }
                data.append(entry)
            result = {"summary": data}
        except SQLAlchemyError:
            self.db.session.rollback()
            result = {"error": "Error encountered while fetching data. Please check logs."}

        return result

    def retrieve_bookkeeping_for_ecosystem(self, ecosystem):
        """Retrieve BookKeeping data for given Ecosystem.

        :param ecosystem: ecosystem for which the data should be retrieved
        """
        try:
            e = Ecosystem.by_name(self.db, ecosystem)
            package_count = self.db.query(Package).filter(Package.ecosystem == e).count()
            pv_count = self.db.query(Version).join(Package).filter(Package.ecosystem == e).count()
            result = {
                "summary": {
                    "ecosystem": e.name,
                    "package_count": package_count,
                    "package_version_count": pv_count
                }
            }
        except NoResultFound:
            result = {"error": "No such ecosystem: %s" % ecosystem}
        except SQLAlchemyError:
            self.db.session.rollback()
            result = {"error": "Error encountered while fetching data. Please check logs."}

        return result

    def retrieve_bookkeeping_for_ecosystem_package(self, ecosystem, package):
        """Retrieve BookKeeping data for given Package and Ecosystem.

        :param ecosystem: ecosystem for which the data should be retrieved
        :param package: package for which the data should be retrieved
        """
        try:
            e = Ecosystem.by_name(self.db, ecosystem)
            p = Package.by_name(self.db, package)
            version_count = self.db.query(Version).join(Package).\
                filter(Package.ecosystem == e).\
                filter(Version.package == p).count()
            stat = self.db.query(PackageWorkerResult.worker, PackageWorkerResult.error,
                                 PackageWorkerResult.task_result).join(PackageAnalysis). \
                filter(PackageAnalysis.package == p).all()

            worker_stats = []
            for worker_name, has_error, task_result in stat:
                entry = {"worker_name": worker_name,
                         "has_error": has_error,
                         "task_result": task_result}
                worker_stats.append(entry)

            p_versions = self.db.query(Version).join(Package).join(Ecosystem).\
                filter(Package.ecosystem == e).\
                filter(Version.package == p)

            result = {
                "summary": {
                    "ecosystem": e.name,
                    "package": p.name,
                    "package_version_count": version_count,
                    "package_level_workers": worker_stats,
                    "analysed_versions": [v.identifier for v in p_versions]
                }
            }
        except NoResultFound:
            result = {"error": "No such package: %s/%s" % (ecosystem, package)}
        except SQLAlchemyError:
            self.db.session.rollback()
            result = {"error": "Error encountered while fetching data. Please check logs."}

        return result

    def retrieve_bookkeeping_for_epv(self, ecosystem, package, version):
        """Retrieve BookKeeping data for the given ecosystem, package, and version.

        :param ecosystem: ecosystem for which the data should be retrieved
        :param package: package for which the data should be retrieved
        :param version: package version for which the data should be retrieved
        """
        try:
            e = Ecosystem.by_name(self.db, ecosystem)
            p = Package.by_name(self.db, package)
            v = self.db.query(Version).join(Package).join(Ecosystem). \
                filter(Package.ecosystem == e). \
                filter(Version.package == p). \
                filter(Version.identifier == version).one()
            stat = self.db.query(WorkerResult.worker,
                                 WorkerResult.error,
                                 WorkerResult.task_result).join(Analysis).join(Version).\
                filter(Analysis.version == v).all()

            worker_stats = []
            for worker_name, has_error, task_result in stat:
                entry = {"worker_name": worker_name,
                         "has_error": has_error,
                         "task_result": task_result}
                worker_stats.append(entry)

            result = {
                "summary": {
                    "ecosystem": e.name,
                    "package": p.name,
                    "version": v.identifier,
                    "workers": worker_stats
                }
            }
        except NoResultFound:
            return {"error": "No such version: %s/%s/%s" % (ecosystem, package, version)}
        except SQLAlchemyError:
            self.db.session.rollback()
            result = {"error": "Error encountered while fetching data. Please check logs."}

        return result
