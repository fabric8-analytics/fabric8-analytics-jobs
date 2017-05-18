from datetime import datetime
from cucoslib.setup_celery import init_celery

from selinon import StoragePool
from cucoslib.models import WorkerResult, Analysis, Package, Version, Ecosystem


def _add_query_datetime_constrains(query, since, until):
    if since:
        query = query.filter(Analysis.started_at.isnot(None))\
            .filter(Analysis.started_at > since)

    if until:
        query = query.filter(Analysis.started_at.isnot(None)) \
            .filter(Analysis.started_at < until)

    return query


def _get_analysis_base_query(db, ecosystem_name, since, until):
    query = db.session.query(Analysis) \
        .join(Version) \
        .join(Package) \
        .join(Ecosystem)\
        .filter(Ecosystem.name == ecosystem_name)
    return _add_query_datetime_constrains(query, since, until)


def _get_finished_analyses_count(db, ecosystem_name, since, until):
    query = _get_analysis_base_query(db, ecosystem_name, since, until)
    return query.filter(Analysis.finished_at.isnot(None)).count()


def _get_unfinished_analyses_count(db, ecosystem_name, since, until):
    query = _get_analysis_base_query(db, ecosystem_name, since, until)
    return query.filter(Analysis.finished_at.is_(None)).count()


def _get_unique_analyses_count(db, ecosystem_name, since, until):
    query = _get_analysis_base_query(db, ecosystem_name, since, until)
    return query.distinct(Version.id).count()


def _get_packages_count(db, ecosystem_name, since, until):
    # We need to make sure that there is at least one worker result for the given package as if the init task fails for
    # some reason, there will be created EPV entries but that package does not exist
    query = db.session.query(WorkerResult) \
        .join(Analysis) \
        .join(Version) \
        .join(Package) \
        .join(Ecosystem)\
        .distinct(Package.id) \
        .filter(Ecosystem.name == ecosystem_name)

    query = _add_query_datetime_constrains(query, since, until)
    return query.count()


def _get_versions_count(db, ecosystem_name, since, until):
    # See _get_packages_count comment why doing this.
    query = db.session.query(WorkerResult) \
        .join(Analysis) \
        .join(Version) \
        .join(Package) \
        .join(Ecosystem)\
        .distinct(Version.id) \
        .filter(Ecosystem.name == ecosystem_name)

    query = _add_query_datetime_constrains(query, since, until)
    return query.count()


def construct_analyses_report(since=None, until=None):
    """Construct analyses state report.
    
    :param since: datetime limitation
    :type since: datetime.datetime
    :param until: datetime limitation
    :type until: datetime.datetime
    :return: a dict describing the current system state
    :rtype: dict
    """
    report = {
        'ecosystems': {},
        'total': {
            'analyses': 0,
            'analyses_finished': 0,
            'analyses_unfinished': 0,
            'analyses_unique': 0,
            'packages': 0,
            'versions': 0
        },
        'since': str(since) if since else None,
        'until': str(until) if until else None,
        'now': str(datetime.now())
    }

    # TODO: init only Selinon
    # there is required only Selinon configuration, we don't need to connect to queues,
    # but let's stick with this for now
    init_celery(result_backend=False)
    db = StoragePool.get_connected_storage('BayesianPostgres')
    ecosystems = db.session.query(Ecosystem).all()

    ecosystem_report = report['ecosystems']
    total_report = report['total']
    for ecosystem in ecosystems:
        ecosystem_name = ecosystem.name

        finished_analyses = _get_finished_analyses_count(db, ecosystem_name, since, until)
        unfinished_analyses = _get_unfinished_analyses_count(db, ecosystem_name, since, until)
        packages = _get_packages_count(db, ecosystem_name, since, until)
        versions = _get_versions_count(db, ecosystem_name, since, until)
        unique_analyses = _get_unique_analyses_count(db, ecosystem_name, since, until)

        ecosystem_report[ecosystem_name] = {
            'ecosystem': ecosystem_name,
            'analyses': finished_analyses + unfinished_analyses,
            'analyses_finished': finished_analyses,
            'analyses_unfinished': unfinished_analyses,
            'analyses_unique': unique_analyses,
            'packages': packages,
            'versions': versions
        }

        total_report['analyses'] += finished_analyses + unfinished_analyses
        total_report['analyses_finished'] += finished_analyses
        total_report['analyses_unfinished'] += unfinished_analyses
        total_report['analyses_unique'] += unique_analyses
        total_report['packages'] += packages
        total_report['versions'] += versions

    return report
