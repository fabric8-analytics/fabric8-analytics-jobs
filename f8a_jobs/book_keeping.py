from selinon import StoragePool
from f8a_worker.models import (Analysis, Ecosystem, Package, Version,
                               WorkerResult, PackageWorkerResult, PackageAnalysis)


def retrieve_bookkeeping(ecosystem=None, package=None, version=None):
    """Retrieve BookKeeping data

    :param ecosystem: ecosystem for which the data should be retrieved
    :param package: package for which the data should be retrieved
    :param version: package version for which the data should be retrieved
    """

    rdb = StoragePool.get_connected_storage('BayesianPostgres')
    db = rdb.session
    result = {}
    if ecosystem is None:
        # return all stats from here
        data = []
        for e in db.query(Ecosystem).all():
            entry = {
                "name": db.query(Ecosystem).get(e.id).name,
                "package_count": db.query(Package).filter(Package.ecosystem == e).count(),
                "package_version_count": db.query(Version).join(Package). \
                    filter(Package.ecosystem == e).count()
            }
            data.append(entry)

        result = {"summary": data}
        return result

    else:
        e = Ecosystem.by_name(db, ecosystem)

        if package is None:
            result = {
                "summary": {
                    "ecosystem": e.name,
                    "package_count": db.query(Package).filter(Package.ecosystem == e).count(),
                    "package_version_count": db.query(Version).join(Package). \
                        filter(Package.ecosystem == e).count()
                }
            }
            return result
        else:
            p = Package.by_name(db, package)

            if version is None:
                # return package stats
                version_count = db.query(Version).join(Package).filter(Package.ecosystem == e). \
                    filter(Version.package == p).count()

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
                return result
            else:
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
                return result

    return result
