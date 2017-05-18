#!/usr/bin/env python3

import traceback
import logging
from dateutil.parser import parse as parse_datetime
from apscheduler.schedulers.base import STATE_STOPPED, JobLookupError

import bayesian_jobs.handlers as handlers
from bayesian_jobs.handlers.base import BaseHandler
from bayesian_jobs.utils import (get_service_state_str, get_job_state_str, job2raw_dict, is_failed_job)
from bayesian_jobs.scheduler import uses_scheduler, ScheduleJobError, Scheduler
from bayesian_jobs.analyses_report import construct_analyses_report

logger = logging.getLogger(__name__)


@uses_scheduler
def get_service_state(scheduler):
    return {"state": get_service_state_str(scheduler)}, 200


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


@uses_scheduler
def delete_jobs(scheduler, job_id):
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        return {"error": "No such job with id '%s'" % job_id}, 401
    return {'removed': [job_id]}, 201


@uses_scheduler
def delete_clean_failed(scheduler):
    ret = []
    for job in scheduler.get_jobs():
        if is_failed_job(job):
            ret.append(job.id)
            job.remove()
    return {'removed': ret}, 201


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
    try:
        # Translate 'kwargs' in POST to handler key-value arguments passing, if needed
        kwargs.update(kwargs.pop('kwargs', {}))
        job = Scheduler.schedule_job(scheduler, handler_name, **kwargs)
        return {"job": job2raw_dict(job)}, 201
    except ScheduleJobError as exc:
        return {"error": str(exc)}, 401


def post_show_select_query(filter_definition):
    try:
        query = BaseHandler(job_id=None).construct_select_query(filter_definition.pop(BaseHandler.DEFAULT_FILTER_KEY))
    except Exception as exc:
        logger.exception(str(exc))
        return {"error": str(exc), "traceback": traceback.format_exc()}, 401
    return {"query": query}, 200


def post_expand_filter_query(filter_definition):
    try:
        matched = BaseHandler(job_id=None).expand_filter_query(filter_definition)
    except Exception as exc:
        logger.exception(str(exc))
        return {"error": str(exc), "traceback": traceback.format_exc()}, 401
    return {"matched": matched}, 200


def get_analyses_report(ecosystem, since=None, until=None):
    if since:
        try:
            since = parse_datetime(since)
        except Exception as exc:
            return {"error": "Cannot parse string format for 'since': %s" % str(exc)}, 400

    if until:
        try:
            until = parse_datetime(until)
        except Exception as exc:
            return {"error": "Cannot parse string format for 'until': %s" % str(exc)}, 400

    return construct_analyses_report(ecosystem, since, until), 200


#
# Handler specific POST requests
#


@uses_scheduler
def post_flow_scheduling(scheduler, **kwargs):
    return post_schedule_job(scheduler, handlers.FlowScheduling.__name__, **kwargs)


@uses_scheduler
def post_selective_flow_scheduling(scheduler, **kwargs):
    return post_schedule_job(scheduler, handlers.SelectiveFlowScheduling.__name__, **kwargs)


@uses_scheduler
def post_popular_analyses(scheduler, **kwargs):
    if kwargs['ecosystem'] == 'maven':
        handler_name = handlers.MavenPopularAnalyses.__name__
    elif kwargs['ecosystem'] == 'npm':
        handler_name = handlers.NpmPopularAnalyses.__name__
    elif kwargs['ecosystem'] == 'pypi':
        handler_name = handlers.PythonPopularAnalyses.__name__
    else:
        return {"error": "Unknown ecosystem '{}'".format(kwargs['ecosystem'])}, 401

    kwargs.pop('ecosystem')
    return post_schedule_job(scheduler, handler_name, **kwargs)


@uses_scheduler
def post_clean_postgres(scheduler, **kwargs):
    return post_schedule_job(scheduler, handlers.CleanPostgres.__name__, **kwargs)

@uses_scheduler
def post_sync_to_graph(scheduler, **kwargs):
    return post_schedule_job(scheduler, handlers.SyncToGraph.__name__, **kwargs)
