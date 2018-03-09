#!/usr/bin/env python3

"""Callback functions called for requests sent to the jobs REST API."""

import traceback
import logging
import requests
from apscheduler.schedulers.base import STATE_STOPPED, JobLookupError
from flask import session, url_for, request
from selinon import StoragePool

import f8a_jobs.handlers as handlers
from f8a_jobs.handlers.base import BaseHandler
from f8a_jobs.utils import (get_service_state_str, get_job_state_str, job2raw_dict, is_failed_job,
                            requires_auth, is_organization_member)
from f8a_jobs.scheduler import uses_scheduler, ScheduleJobError, Scheduler
from f8a_jobs.analyses_report import construct_analyses_report
from f8a_jobs.utils import construct_queue_attributes
from f8a_jobs.utils import purge_queues
from f8a_jobs.utils import parse_dates
from f8a_jobs.auth import github
from f8a_jobs.models import JobToken
from f8a_jobs.defaults import AUTH_ORGANIZATION
from f8a_jobs.defaults import DATA_IMPORTER_ENDPOINT
import f8a_jobs.defaults as configuration
from f8a_jobs import graph_sync
import json

logger = logging.getLogger(__name__)


def generate_token():
    """Generate the authorization token via GitHub service."""
    return github.authorize(callback=url_for('/api/v1.f8a_jobs_api_v1_authorized',
                            _external=True))


def logout():
    """Logout from the Job service (if the user is already loged in)."""
    if 'auth_token' not in session:
        return {}, 401

    session.pop('auth_token')
    return {}, 201


def authorized():
    """Perform authorization via GitHub service."""
    auth_token = request.headers.get('auth_token')
    if 'auth_token' in session:
        # Authorization token in session has higher priority
        auth_token = session.get('auth_token', (None,))[0]

    if auth_token:
        info = JobToken.get_info(auth_token)
        if 'token' in info and 'error' not in info:
            # The token is already in our DB - we can trust this fella
            return info

    logger.info("Authorized redirection triggered, getting authorized response from Github")
    resp = github.authorized_response()
    logger.info("Got Github authorized response")

    if resp is None or resp.get('access_token') is None:
        msg = 'Access denied: reason=%s error=%s resp=%s' % (
            request.args['error'],
            request.args['error_description'],
            resp
        )
        logger.warning(msg)
        return {'error': msg}, 400

    logger.debug("Assigning authorization token '%s' to session", resp['access_token'])
    session['auth_token'] = (resp['access_token'], '')
    oauth_info = github.get('user')
    if not is_organization_member(oauth_info.data, resp['access_token']):
        logger.debug("User '%s' is not member of organization '%s'", oauth_info.data['login'],
                     AUTH_ORGANIZATION)
        logout()
        return {'error': 'unauthorized'}, 401

    token_info = JobToken.store_token(oauth_info.data['login'], resp['access_token'])
    return token_info


@requires_auth
@uses_scheduler
def get_service_state(scheduler):
    """Return the current state of the job service."""
    return {"state": get_service_state_str(scheduler)}, 200


@requires_auth
@uses_scheduler
def put_service_state(scheduler, state):
    """Change the state of the job service."""
    if scheduler.state == STATE_STOPPED:
        scheduler.start(paused=(state == 'paused'))

    if state == 'paused':
        scheduler.pause()
    elif state == 'running':
        scheduler.resume()
    else:
        return {"error": "Unknown status provided: '%s'" % state}, 400

    return {"state": get_service_state_str(scheduler)}, 200


@requires_auth
@uses_scheduler
def delete_jobs(scheduler, job_id):
    """Delete job with given job ID."""
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        return {"error": "No such job with id '%s'" % job_id}, 410
    return {'removed': [job_id]}, 200


@requires_auth
@uses_scheduler
def delete_clean_failed(scheduler):
    """Clean up all failed jobs."""
    ret = []
    for job in scheduler.get_jobs():
        if is_failed_job(job):
            ret.append(job.id)
            job.remove()
    return {'removed': ret}, 200


@requires_auth
@uses_scheduler
def put_jobs(scheduler, job_id, state):
    """Change the state of job specified by its ID."""
    try:
        if state == "paused":
            job = scheduler.pause_job(job_id)
        elif state == "running":
            job = scheduler.resume_job(job_id)
        else:
            return {"error": "Unknown state '%s'" % state}, 400
    except JobLookupError:
        return {"error": "No such job with id '%s'" % job_id}, 404

    return {"job_id": job.id, "state": get_job_state_str(job)}, 200


@requires_auth
@uses_scheduler
def get_jobs(scheduler, job_type=None):
    """Retrieve all active jobs or all jobs of specified type."""
    jobs = scheduler.get_jobs()

    job_types = ('all', 'failed', 'user', None)
    if job_type not in job_types:
        return {"error": "Unknown job type filtering supplied: '%s', should be one of %s" %
                (job_type, job_types)}, 400

    job_list = []
    job_type = job_type or 'all'
    for job in jobs:
        if job_type == 'failed' and is_failed_job(job):
                job_list.append(job2raw_dict(job))
        if job_type == 'user' and not is_failed_job(job):
            job_list.append(job2raw_dict(job))
        if job_type == 'all':
            job_list.append(job2raw_dict(job))

    return {"jobs": job_list, "jobs_count": len(job_list)}, 200


def get_readiness():
    """Get job service readiness."""
    return {}, 200


@uses_scheduler
def get_liveness(scheduler):
    """Get job service liveness."""
    # Ensure the scheduler is alive
    logger.warning("Liveness probe - trying retrieve stored jobs from database using scheduler")
    # Ensure that we are able to publish messages
    logger.warning("Liveness probe - trying to schedule the livenessFlow")
    handlers.FlowScheduling(job_id=None).execute('livenessFlow', flow_arguments=[None])
    logger.warning("Liveness probe - finished")
    return {}, 200


def post_schedule_job(scheduler, handler_name, **kwargs):
    """Schedule the new job specified by its name and parameters."""
    # No need to add @requires_auth for this one, assuming handler specific
    # POST endpoints take care of it
    try:
        # Translate 'kwargs' in POST to handler key-value arguments passing, if needed
        kwargs.update(kwargs.pop('kwargs', {}))
        job = Scheduler.schedule_job(scheduler, handler_name, **kwargs)
        return {"job": job2raw_dict(job)}, 201
    except ScheduleJobError as exc:
        return {"error": str(exc)}, 400


@requires_auth
def post_show_select_query(filter_definition):
    """Show SQL query that will be used in case of filter parametrized jobs."""
    try:
        from json2sql.select import DEFAULT_FILTER_KEY
        query = BaseHandler(job_id=None).construct_select_query(filter_definition.pop(
            DEFAULT_FILTER_KEY))
    except Exception as exc:
        logger.exception(str(exc))
        return {"error": str(exc), "traceback": traceback.format_exc()}, 400
    return {"query": query}, 200


@requires_auth
def post_expand_filter_query(filter_definition):
    """Use filter to query database and show results that matched given filter."""
    try:
        matched = BaseHandler(job_id=None).expand_filter_query(filter_definition)
    except Exception as exc:
        logger.exception(str(exc))
        return {"error": str(exc), "traceback": traceback.format_exc()}, 400
    return {"matched": matched}, 200


@requires_auth
def get_analyses_report(**kwargs):
    """View brief report of the current system analyses status."""
    try:
        parse_dates(kwargs)
    except Exception as exc:
        return {'error': str(exc)}, 400
    return construct_analyses_report(**kwargs), 200


@requires_auth
def get_queue_attributes():
    """Generate report containing queue attributes info."""
    try:
        report = construct_queue_attributes()
    except Exception as exc:
        logger.exception("Failed to get queue attributes")
        return {"error": str(exc)}, 500
    return report, 200


@requires_auth
def get_gh_tokens_rate_limits():
    """Show current API rate limits on GitHub tokens."""
    response = {'tokens': []}
    for token in configuration.GITHUB_ACCESS_TOKENS:
        r = requests.get('https://api.github.com/rate_limit', params={'access_token': token})
        limits = r.json()
        limits['token'] = '{prefix}...'.format(prefix=token[:4])
        response['tokens'].append(limits)

    return response, 200

#
# Handler specific POST requests
#


@requires_auth
@uses_scheduler
def post_flow_scheduling(scheduler, **kwargs):
    """Schedule the job with configuration based on the JSON structure send via request."""
    return post_schedule_job(scheduler, handlers.FlowScheduling.__name__, **kwargs)


@requires_auth
@uses_scheduler
def post_selective_flow_scheduling(scheduler, **kwargs):
    """Schedule the job with configuration based on the JSON structure send via request."""
    return post_schedule_job(scheduler, handlers.SelectiveFlowScheduling.__name__, **kwargs)


@requires_auth
@uses_scheduler
def post_analyses(scheduler, **kwargs):
    """Schedule the job to run analysis for selected ecosystem."""
    try:
        handlers.base.AnalysesBaseHandler.check_arguments(**kwargs)
    except Exception as exc:
        return {"error": str(exc)}, 400

    handler_name = handlers.base.AnalysesBaseHandler.ecosystem2handler_name(kwargs['ecosystem'])
    return post_schedule_job(scheduler, handler_name, **kwargs)


@requires_auth
@uses_scheduler
def github_most_starred(scheduler, **kwargs):
    """Schedule the job to read GitHub most starred repositories."""
    try:
        handlers.base.AnalysesBaseHandler.check_arguments(**kwargs)
    except Exception as exc:
        return {"error": str(exc)}, 400

    return post_schedule_job(scheduler, handlers.GitHubMostStarred.__name__, **kwargs)


@requires_auth
@uses_scheduler
def github_manifests(scheduler, **kwargs):
    """Collect and process manifest files from given GitHub repositories."""
    return post_schedule_job(scheduler, handlers.GitHubManifests.__name__, **kwargs)


@requires_auth
@uses_scheduler
def aggregate_crowd_source_tags(scheduler, **kwargs):
    """Aggregate crowd source tags."""
    return post_schedule_job(scheduler, handlers.AggregateCrowdSourceTags.__name__, **kwargs)


@requires_auth
@uses_scheduler
def aggregate_github_manifest_pkgs(scheduler, **kwargs):
    """Aggregate package names from GitHub manifests."""
    return post_schedule_job(scheduler, handlers.AggregateGitHubManifestPackages.__name__, **kwargs)


@requires_auth
@uses_scheduler
def post_clean_postgres(scheduler, **kwargs):
    """Clean PostgreSQL results."""
    try:
        parse_dates(kwargs)
    except Exception as exc:
        return {'error': str(exc)}, 400
    return post_schedule_job(scheduler, handlers.CleanPostgres.__name__, **kwargs)


@requires_auth
@uses_scheduler
def post_sync_to_graph(scheduler, **kwargs):
    """Sync all finished analyses to graph."""
    return post_schedule_job(scheduler, handlers.SyncToGraph.__name__, **kwargs)


@requires_auth
@uses_scheduler
def post_invoke_graph_sync(scheduler, **kwargs):
    """Sync all finished analyses to graph."""
    return post_schedule_job(scheduler, handlers.InvokeGraphSync.__name__, **kwargs)


@requires_auth
@uses_scheduler
def post_aggregate_topics(scheduler, **kwargs):
    """Aggregate all topics collected from GitHub and store them on S3."""
    return post_schedule_job(scheduler, handlers.AggregateTopics.__name__, **kwargs)


@requires_auth
def post_queue_purge(queues):
    """Purge given SQS queues."""
    try:
        report = purge_queues(queues.split(','))
    except Exception as exc:
        return {'error': str(exc)}, 500
    return report, 200


@requires_auth
@uses_scheduler
def post_maven_releases(scheduler, **kwargs):
    """Add job for scheduling new maven releases."""
    return post_schedule_job(scheduler, handlers.MavenReleasesAnalyses.__name__, **kwargs)


@requires_auth
def get_maven_releases():
    """Get last used offset to maven indexer."""
    s3 = StoragePool.get_connected_storage('S3MavenIndex')
    return {'last_offset': s3.get_last_offset()}, 200


@requires_auth
def put_maven_releases(offset):
    """Adjust offset to maven indexer that should be used."""
    s3 = StoragePool.get_connected_storage('S3MavenIndex')
    s3.set_last_offset(offset)
    return {'last_offset': s3.get_last_offset()}, 201


@requires_auth
def bookkeeping_all():
    """Retrieve BookKeeping data for all Ecosystems."""
    result = handlers.BookKeeping().retrieve_bookkeeping_all()
    return result


@requires_auth
def bookkeeping_ecosystem(ecosystem):
    """Retrieve BookKeeping data for given Ecosystem."""
    result = handlers.BookKeeping().retrieve_bookkeeping_for_ecosystem(ecosystem)
    return result


@requires_auth
def bookkeeping_ecosystem_package(ecosystem, package):
    """Retrieve BookKeeping data for given Package and Ecosystem."""
    result = handlers.BookKeeping().retrieve_bookkeeping_for_ecosystem_package(ecosystem, package)
    return result


@requires_auth
def bookkeeping_epv(ecosystem, package, version):
    """Retrieve BookKeeping data for the given ecosystem, package, and version."""
    result = handlers.BookKeeping().retrieve_bookkeeping_for_epv(ecosystem, package, version)
    return result


@requires_auth
def bookkeeping_upstreams_all(**kwargs):
    """Retrieve list of monitored upstreams."""
    result = handlers.BookKeeping().retrieve_bookkeeping_upstreams(**kwargs)
    return result


@requires_auth
def bookkeeping_upstreams_ecosystem(**kwargs):
    """Retrieve list of monitored upstreams for give ecosystem."""
    result = handlers.BookKeeping().retrieve_bookkeeping_upstreams(**kwargs)
    return result


@requires_auth
def bookkeeping_upstreams_ecosystem_package(**kwargs):
    """Retrieve list of monitored upstreams for given ecosystem and package."""
    result = handlers.BookKeeping().retrieve_bookkeeping_upstreams(**kwargs)
    return result


@requires_auth
@uses_scheduler
def post_kronos_data_update(scheduler, **kwargs):
    """Aggregate package names from GitHub manifests."""
    return post_schedule_job(scheduler, handlers.KronosDataUpdater.__name__, **kwargs)


# Graph Sync pending list APIs
@requires_auth
def retrieve_graphsync_all(**kwargs):
    """Retrieve Pending Graph Sync data for all Ecosystems."""
    result = graph_sync.fetch_pending(params=kwargs)
    return result


@requires_auth
def retrieve_graphsync_ecosystem(**kwargs):
    """Retrieve Pending Graph Sync data for given ecosystem."""
    result = graph_sync.fetch_pending(params=kwargs)
    return result


@requires_auth
def retrieve_graphsync_ecosystem_package(**kwargs):
    """Retrieve Pending Graph Sync data for given ecosystem and package.

    :param ecosystem: ecosystem for which the data should be retrieved
    :param package: package for which the data should be retrieved
    """
    result = graph_sync.fetch_pending(params=kwargs)
    return result


@requires_auth
def retrieve_graphsync_epv(**kwargs):
    """Retrieve Pending Graph Sync data for the given ecosystem, package, and version.

    :param ecosystem: ecosystem for which the data should be retrieved
    :param package: package for which the data should be retrieved
    :param version: package version for which the data should be retrieved
    """
    result = graph_sync.fetch_pending(params=kwargs)
    return result


# Graph Sync sync_all APIs
@requires_auth
def invoke_graphsync_all(**kwargs):
    """Invoke Pending Graph Sync data for all Ecosystems."""
    result = graph_sync.invoke_sync(params=kwargs)
    return result


@requires_auth
def invoke_graphsync_ecosystem(**kwargs):
    """Invoke Pending Graph Sync data for given ecosystem."""
    result = graph_sync.invoke_sync(params=kwargs)
    return result


@requires_auth
def invoke_graphsync_ecosystem_package(**kwargs):
    """Invoke Pending Graph Sync data for given ecosystem and package.

    :param ecosystem: ecosystem for which the data should be retrieved
    :param package: package for which the data should be retrieved
    """
    result = graph_sync.invoke_sync(params=kwargs)
    return result


@requires_auth
def invoke_graphsync_epv(**kwargs):
    """Invoke Pending Graph Sync data for the given ecosystem, package, and version.

    :param ecosystem: ecosystem for which the data should be retrieved
    :param package: package for which the data should be retrieved
    :param version: package version for which the data should be retrieved
    """
    result = graph_sync.invoke_sync(params=kwargs)
    return result


@requires_auth
def api_gateway(**kwargs):
    """Call f8a service based on request parameters.

    :param service_name: service that should be called
    :param service_endpoint: service endpoint that should be called
    :param data_for_service: data for the service in json
    """
    service_endpoint = kwargs.get("service_endpoint", None)
    uri = DATA_IMPORTER_ENDPOINT + service_endpoint

    if request.method == 'POST':
        result = requests.post(uri, json=json.dumps(kwargs.get("data_for_service", None)))

    elif request.method == 'GET':
        result = requests.get(uri, params=kwargs.get("data_for_service", None))

    return result
