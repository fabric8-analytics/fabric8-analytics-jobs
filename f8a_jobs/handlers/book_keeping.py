"""Class to retrieve BookKeeping data."""

from functools import wraps
from selinon import StoragePool
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import SQLAlchemyError
from f8a_worker.models import (Analysis, Ecosystem, Package, Version,
                               WorkerResult, PackageWorkerResult, PackageAnalysis,
                               Upstream)
from .base import AnalysesBaseHandler


def handle_sqlalchemy(func):
    """Decorate repeating code."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        """Wrap sqlalchemy code into try-except."""
        try:
            data = func(*args, **kwargs)
            result = {"summary": data}
        except NoResultFound:
            result = {"error": "No result found."}
        except SQLAlchemyError:
            StoragePool.get_connected_storage('BayesianPostgres').session.rollback()
            result = {"error": "SQLAlchemyError encountered while fetching data. "
                               "Roll-backing. Try again."}
        return result
    return wrapper


class BookKeeping(object):
    """Class to retrieve BookKeeping data."""

    def __init__(self):
        """Initialize instance."""
        rdb = StoragePool.get_connected_storage('BayesianPostgres')
        self.db = rdb.session

    @handle_sqlalchemy
    def retrieve_bookkeeping_all(self):
        """Retrieve BookKeeping data for all Ecosystems."""
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
        return data

    @handle_sqlalchemy
    def retrieve_bookkeeping_for_ecosystem(self, ecosystem):
        """Retrieve BookKeeping data for given Ecosystem.

        :param ecosystem: ecosystem for which the data should be retrieved
        """
        e = Ecosystem.by_name(self.db, ecosystem)
        package_count = self.db.query(Package).filter(Package.ecosystem == e).count()
        pv_count = self.db.query(Version).join(Package).filter(Package.ecosystem == e).count()
        return {"ecosystem": e.name,
                "package_count": package_count,
                "package_version_count": pv_count}

    @handle_sqlalchemy
    def retrieve_bookkeeping_for_ecosystem_package(self, ecosystem, package):
        """Retrieve BookKeeping data for given Package and Ecosystem.

        :param ecosystem: ecosystem for which the data should be retrieved
        :param package: package for which the data should be retrieved
        """
        e = Ecosystem.by_name(self.db, ecosystem)
        p = Package.by_name(self.db, package)

        stat = self.db.query(PackageWorkerResult).\
            join(PackageAnalysis).\
            filter(PackageAnalysis.package == p)
        worker_stats = []
        for package_worker_result in stat.all():
            entry = {"worker_name": package_worker_result.worker,
                     "has_error": package_worker_result.error,
                     "task_result": package_worker_result.task_result,
                     "started_at": package_worker_result.started_at,
                     "ended_at": package_worker_result.ended_at}
            worker_stats.append(entry)

        version_count = self.db.query(Version).join(Package).\
            filter(Package.ecosystem == e).\
            filter(Version.package == p).count()
        p_versions = self.db.query(Version).join(Package).join(Ecosystem).\
            filter(Package.ecosystem == e).\
            filter(Version.package == p)

        return {"ecosystem": e.name,
                "package": p.name,
                "package_version_count": version_count,
                "package_level_workers": worker_stats,
                "analysed_versions": [v.identifier for v in p_versions]}

    @handle_sqlalchemy
    def retrieve_bookkeeping_for_epv(self, ecosystem, package, version):
        """Retrieve BookKeeping data for the given ecosystem, package, and version.

        :param ecosystem: ecosystem for which the data should be retrieved
        :param package: package for which the data should be retrieved
        :param version: package version for which the data should be retrieved
        """
        e = Ecosystem.by_name(self.db, ecosystem)
        p = Package.by_name(self.db, package)
        v = self.db.query(Version).join(Package).join(Ecosystem). \
            filter(Package.ecosystem == e). \
            filter(Version.package == p). \
            filter(Version.identifier == version).one()

        stat = self.db.query(WorkerResult).\
            join(Analysis).join(Version).\
            filter(Analysis.version == v)
        worker_stats = []
        for worker_result in stat.all():
            entry = {"worker_name": worker_result.worker,
                     "has_error": worker_result.error,
                     "task_result": worker_result.task_result,
                     "started_at": worker_result.started_at,
                     "ended_at": worker_result.ended_at}
            worker_stats.append(entry)

        return {"ecosystem": e.name,
                "package": p.name,
                "version": v.identifier,
                "workers": worker_stats}

    @handle_sqlalchemy
    def retrieve_bookkeeping_upstreams(self,
                                       ecosystem=None, package=None, active_only=None, count=None):
        """Retrieve BookKeeping data for monitored upstreams."""
        count = count and AnalysesBaseHandler.parse_count(count)

        query = self.db.query(Upstream, Package.name, Ecosystem.name).\
            join(Package).join(Ecosystem)
        query = query.filter(Ecosystem.name == ecosystem) if ecosystem \
            else query.filter(Ecosystem.id == Package.ecosystem_id)
        query = query.filter(Package.name == package) if package \
            else query.filter(Package.id == Upstream.package_id)
        if active_only:
            query = query.filter(Upstream.deactivated_at.is_(None))

        results = query[count.min - 1:count.max] if count else query.all()
        data = [{"ecosystem_package": "{}/{}".format(e, p),
                 "url": u.url,
                 "updated_at": u.updated_at,
                 "added_at": u.added_at,
                 "deactivated_at": u.deactivated_at} for u, p, e in results]
        return data
