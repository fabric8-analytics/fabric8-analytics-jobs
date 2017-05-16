#!/usr/bin/env python3

import traceback
import logging
from flask import session, url_for, request
from apscheduler.schedulers.base import STATE_STOPPED, JobLookupError

import bayesian_jobs.handlers as handlers
from bayesian_jobs.handlers.base import BaseHandler
from bayesian_jobs.utils import get_service_state_str, get_job_state_str, job2raw_dict, is_failed_job, requires_auth, \
    is_organization_member
from bayesian_jobs.scheduler import uses_scheduler, ScheduleJobError, Scheduler
from bayesian_jobs.auth import github
from bayesian_jobs.models import JobToken
from bayesian_jobs.configuration import AUTH_ORGANIZATION

logger = logging.getLogger(__name__)


def generate_token():
    return github.authorize(callback=url_for('/api/v1.bayesian_jobs_api_v1_authorized', _external=True))


def logout():
    session.pop('auth_token', None)
    return {}, 201


def authorized():
    if 'auth_token' in session and isinstance(session['auth_token'], tuple) and session['auth_token']:
        return JobToken.get_info(session.get('auth_token', (None,))[0])

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
        return {'error': msg}, 401

    logger.debug("Assigning authorization token '%s' to session", resp['access_token'])
    session['auth_token'] = (resp['access_token'], '')
    oauth_info = github.get('user')
    if not is_organization_member(oauth_info.data):
        logger.debug("User '%s' is not member of organization '%s'", oauth_info.data['login'], AUTH_ORGANIZATION)
        logout()
        return {'error': 'unauthorized'}, 401

    token_info = JobToken.store_token(oauth_info.data['login'], resp['access_token'])
    return token_info


@requires_auth
@uses_scheduler
def get_service_state(scheduler):
    return {"state": get_service_state_str(scheduler)}, 200


@requires_auth
@uses_scheduler
def put_service_state(scheduler, state):
    if scheduler.state == STATE_STOPPED:
        scheduler.start(paused=(state == 'paused'))

    if state == 'paused':
        scheduler.pause()
    elif state == 'running':
        scheduler.resume()
    else:
        return {"error": "Unknown status provided: '%s'" % state}, 400

    return {"state": get_service_state_str(scheduler)}, 201


@requires_auth
@uses_scheduler
def delete_jobs(scheduler, job_id):
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        return {"error": "No such job with id '%s'" % job_id}, 401
    return {'removed': [job_id]}, 201


@requires_auth
@uses_scheduler
def delete_clean_failed(scheduler):
    ret = []
    for job in scheduler.get_jobs():
        if is_failed_job(job):
            ret.append(job.id)
            job.remove()
    return {'removed': ret}, 201


@requires_auth
@uses_scheduler
def put_jobs(scheduler, job_id, state):
    try:
        if state == "paused":
            job = scheduler.pause_job(job_id)
        elif state == "running":
            job = scheduler.resume_job(job_id)
        else:
            return {"error": "Unknown state '%s'" % state}, 401
    except JobLookupError:
        return {"error": "No such job with id '%s'" % job_id}, 401

    return {"job_id": job.id, "state": get_job_state_str(job)}, 201


@requires_auth
@uses_scheduler
def get_jobs(scheduler, job_type=None):
    jobs = scheduler.get_jobs()

    job_types = ('all', 'failed', 'user', None)
    if job_type not in job_types:
        return {"error": "Unknown job type filtering supplied: '%s', should be one of %s" % (job_type, job_types)}, 401

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
    return {}, 200


@uses_scheduler
def get_liveness(scheduler):
    # Ensure the scheduler is alive
    logger.warning("Liveness probe - trying retrieve stored jobs from database using scheduler")
    # Ensure that we are able to publish messages
    logger.warning("Liveness probe - trying to schedule the livenessFlow")
    handlers.FlowScheduling(job_id=None).execute('livenessFlow', flow_arguments=[None])
    logger.warning("Liveness probe - finished")
    return {}, 200


def post_schedule_job(scheduler, handler_name, **kwargs):
    # No need to add @requires_auth for this one, assuming handler specific POST endpoints take care of it
    try:
        # Translate 'kwargs' in POST to handler key-value arguments passing, if needed
        kwargs.update(kwargs.pop('kwargs', {}))
        job = Scheduler.schedule_job(scheduler, handler_name, **kwargs)
        return {"job": job2raw_dict(job)}, 201
    except ScheduleJobError as exc:
        return {"error": str(exc)}, 401


@requires_auth
def post_show_select_query(filter_definition):
    try:
        query = BaseHandler(job_id=None).construct_select_query(filter_definition.pop(BaseHandler.DEFAULT_FILTER_KEY))
    except Exception as exc:
        logger.exception(str(exc))
        return {"error": str(exc), "traceback": traceback.format_exc()}, 401
    return {"query": query}, 200


@requires_auth
def post_expand_filter_query(filter_definition):
    try:
        matched = BaseHandler(job_id=None).expand_filter_query(filter_definition)
    except Exception as exc:
        logger.exception(str(exc))
        return {"error": str(exc), "traceback": traceback.format_exc()}, 401
    return {"matched": matched}, 200

#
# Handler specific POST requests
#


@requires_auth
@uses_scheduler
def post_flow_scheduling(scheduler, **kwargs):
    return post_schedule_job(scheduler, handlers.FlowScheduling.__name__, **kwargs)


@requires_auth
@uses_scheduler
def post_selective_flow_scheduling(scheduler, **kwargs):
    return post_schedule_job(scheduler, handlers.SelectiveFlowScheduling.__name__, **kwargs)


@requires_auth
@uses_scheduler
def post_popular_analyses(scheduler, **kwargs):
    if kwargs['ecosystem'] == 'maven':
        handler_name = handlers.MavenPopularAnalyses.__name__
    elif kwargs['ecosystem'] == 'npm':
        handler_name = handlers.NpmPopularAnalyses.__name__
    elif kwargs['ecosystem'] == 'python':
        handler_name = handlers.PythonPopularAnalyses.__name__
    else:
        return {"error": "Unknown ecosystem '{}'".format(kwargs['ecosystem'])}, 401

    kwargs.pop('ecosystem')
    return post_schedule_job(scheduler, handler_name, **kwargs)


@requires_auth
@uses_scheduler
def post_clean_postgres(scheduler, **kwargs):
    return post_schedule_job(scheduler, handlers.CleanPostgres.__name__, **kwargs)


@requires_auth
@uses_scheduler
def post_sync_to_graph(scheduler, **kwargs):
    return post_schedule_job(scheduler, handlers.SyncToGraph.__name__, **kwargs)
