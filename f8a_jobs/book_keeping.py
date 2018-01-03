from selinon import StoragePool
from f8a_worker.models import (Analysis, Ecosystem, Package, Version,
                               WorkerResult, PackageWorkerResult, PackageAnalysis)
from sqlalchemy.orm.exc import NoResultFound
from f8a_jobs.analyses_report import _count
from sqlalchemy.exc import SQLAlchemyError


def retrieve_bookkeeping_all():
    """
    Retrieve BookKeeping data for all Ecosystems
    """

    rdb = StoragePool.get_connected_storage('BayesianPostgres')
    db = rdb.session
    try:
        data = []
        for e in db.query(Ecosystem).all():
            package_count = _count(db, db.query(Package).filter(Package.ecosystem == e))
            ecosystem_name = db.query(Ecosystem).get(e.id).name
            pv_count = _count(db, db.query(Version).join(Package).filter(Package.ecosystem == e))
            entry = {
                "name": ecosystem_name,
                "package_count": package_count,
                "package_version_count": pv_count
            }
            data.append(entry)

        result = {"summary": data}

    except SQLAlchemyError as e:
        result = {"error": "Error encountered while fetching data. Please check logs."}

    return result


def retrieve_bookkeeping_for_ecosystem(ecosystem):
    """
    Retrieve BookKeeping data for given Ecosystem

    :param ecosystem: ecosystem for which the data should be retrieved
    """

    rdb = StoragePool.get_connected_storage('BayesianPostgres')
    db = rdb.session
    try:
        e = Ecosystem.by_name(db, ecosystem)
        package_count = _count(db, db.query(Package).filter(Package.ecosystem == e))
        pv_count = _count(db, db.query(Version).join(Package).filter(Package.ecosystem == e))
        result = {
            "summary": {
                "ecosystem": e.name,
                "package_count": package_count,
                "package_version_count": pv_count
            }
        }
    except NoResultFound as e:
        result = {"error": "No such ecosystem: %s" % ecosystem}
    except SQLAlchemyError as e:
        result = {"error": "Error encountered while fetching data. Please check logs."}

    return result


def retrieve_bookkeeping_for_ecosystem_package(ecosystem, package):
    """
    Retrieve BookKeeping data for given Package and Ecosystem

    :param ecosystem: ecosystem for which the data should be retrieved
    :param package: package for which the data should be retrieved
    """

    rdb = StoragePool.get_connected_storage('BayesianPostgres')
    db = rdb.session

    try:
        e = Ecosystem.by_name(db, ecosystem)
        p = Package.by_name(db, package)

        version_count = _count(db, db.query(Version).join(Package).filter(Package.ecosystem == e).
                               filter(Version.package == p))

        stat = db.query(PackageWorkerResult.worker, PackageWorkerResult.error,
                        PackageWorkerResult.task_result).join(PackageAnalysis). \
            filter(PackageAnalysis.package == p). \
            all()

        worker_stats = []
        for worker_name, has_error, task_result in stat:
            entry = {"worker_name": worker_name,
                     "has_error": has_error,
                     "task_result": task_result}
            worker_stats.append(entry)

        p_versions = db.query(Version).join(Package).join(Ecosystem). \
            filter(Package.ecosystem == e). \
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
    except NoResultFound as e:
        result = {"error": "No such package: %s/%s" % (ecosystem, package)}
    except SQLAlchemyError as e:
        result = {"error": "Error encountered while fetching data. Please check logs."}
    return result


def retrieve_bookkeeping_for_epv(ecosystem, package, version):
    """Retrieve BookKeeping data

    :param ecosystem: ecosystem for which the data should be retrieved
    :param package: package for which the data should be retrieved
    :param version: package version for which the data should be retrieved
    """

    rdb = StoragePool.get_connected_storage('BayesianPostgres')
    db = rdb.session
    try:
        e = Ecosystem.by_name(db, ecosystem)
        p = Package.by_name(db, package)
        v = db.query(Version).join(Package).join(Ecosystem). \
            filter(Package.ecosystem == e). \
            filter(Version.package == p). \
            filter(Version.identifier == version).one()

        stat = db.query(WorkerResult.worker, WorkerResult.error, WorkerResult.task_result). \
            join(Analysis).join(Version). \
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
    except NoResultFound as e:
        return {"error": "No such version: %s/%s/%s" % (ecosystem, package, version)}
    except SQLAlchemyError as e:
        result = {"error": "Error encountered while fetching data. Please check logs."}
    return result
