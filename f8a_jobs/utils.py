#!/usr/bin/env python3
import logging
import os
import boto3
from functools import wraps
import requests
import random
from datetime import timedelta
from datetime import timezone
from flask import request, abort
from apscheduler.schedulers.base import STATE_RUNNING, STATE_STOPPED
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
import f8a_jobs.defaults as configuration
from f8a_jobs.handlers.error import ErrorHandler
from f8a_jobs.models import JobToken
from f8a_jobs.error import TokenExpired

logger = logging.getLogger(__name__)


def get_service_state_str(scheduler):
    """Get string representation of service state/scheduler"""
    if scheduler.state == STATE_RUNNING:
        return 'running'
    elif scheduler.state == STATE_STOPPED:
        return 'stopped'
    else:
        return 'paused'


def get_job_state_str(job):
    """Get string representation of a job"""
    if not hasattr(job, 'next_run_time'):
        # based on apscheduler sources
        return 'pending'
    elif job.next_run_time is None:
        return 'paused'
    else:
        return 'active'


def is_failed_job(job):
    """
    :param job: job to check
    :return: True if the given job is an error handler job
    """
    return is_failed_job_handler_name(job.args[0])


def is_failed_job_handler_name(handler_name):
    """
    :param handler_name: job handler name
    :return: True if job handler is an error handler
    """
    return handler_name == ErrorHandler.__name__


def job2raw_dict(job):
    """Return a dictionary for the given job that is JSON serializable"""
    result = {
        'job_id': job.id,
        'handler': job.args[0],
        'kwargs': job.kwargs,
        'state': get_job_state_str(job),
    }

    if isinstance(job.trigger, DateTrigger):
        result['when'] = job.trigger.run_date.astimezone(tz=timezone.utc).isoformat()
        result['periodically'] = False
    elif isinstance(job.trigger, IntervalTrigger):
        result['when'] = job.trigger.start_date.astimezone(tz=timezone.utc).isoformat()
        result['periodically'] = str(timedelta(seconds=job.trigger.interval_length))

    if hasattr(job, 'misfire_grace_time') and job.misfire_grace_time is not None:
        result['misfire_grace_time'] = str(timedelta(seconds=job.misfire_grace_time))

    return result


def requires_auth(func):
    """ Verify authentication token sent in header

    :param func: function that should be called if verification succeeds
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if configuration.DISABLE_AUTHENTICATION:
            return func(*args, **kwargs)

        auth_token = request.headers.get('auth_token')
        try:
            if not JobToken.verify(auth_token):
                logger.info("Verification for token '%s' failed", auth_token)
                abort(401)
        except TokenExpired:
            abort(401, "Token has expired, logout and generate a new one")

        return func(*args, **kwargs)

    return wrapper


def is_organization_member(user_data):
    """ Check that a user is a member of organization

    :param user_data: user OAuth data
    :return: True if user is a member of organization
    """
    data = requests.get(user_data['organizations_url'], params={'access_token': get_gh_token()})
    data.raise_for_status()
    return any(org_def['login'] == configuration.AUTH_ORGANIZATION for org_def in data.json())


def get_gh_token():
    return random.choice(configuration.GITHUB_ACCESS_TOKENS).strip()


def construct_queue_attributes():
    """Retrieve relevant attributes about queues in the given deployment."""
    if not configuration.AWS_ACCESS_KEY_ID or not configuration.AWS_SECRET_ACCESS_KEY:
        raise ValueError('Missing AWS credentials')

    client = boto3.client('sqs',
                          aws_access_key_id=configuration.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=configuration.AWS_SECRET_ACCESS_KEY,
                          region_name=configuration.AWS_SQS_REGION)

    response = client.list_queues(QueueNamePrefix=configuration.DEPLOYMENT_PREFIX)
    queue_urls = response.get('QueueUrls')

    if not queue_urls:
        raise RuntimeError("No queue urls in response: %r" % str(response))

    result = {}
    for queue_url in queue_urls:
        queue_info = client.get_queue_attributes(QueueUrl=queue_url,
                                                 AttributeNames=[
                                                     'ApproximateNumberOfMessages'
                                                 ])
        queue_name = queue_url.rsplit('/', 1)[-1]
        result[queue_name] = queue_info.pop('Attributes', {})

        # Convert strings that are actually integers
        for attribute, value in result[queue_name].items():
            if attribute == 'ApproximateNumberOfMessages':
                result[queue_name][attribute] = int(value)

    return result


def purge_queues(queues):
    """Purge given SQS queues.

    :param queues: a list of queues to be purged
    :type queues: list
    """
    if not configuration.AWS_ACCESS_KEY_ID or not configuration.AWS_SECRET_ACCESS_KEY:
        raise ValueError('Missing AWS credentials')

    client = boto3.client('sqs', aws_access_key_id=configuration.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=configuration.AWS_SECRET_ACCESS_KEY,
                          region_name=configuration.AWS_SQS_REGION)

    purged = []
    for queue in queues:
        queue_name = '{prefix}_{queue}'.format(prefix=configuration.DEPLOYMENT_PREFIX,
                                               queue=queue)

        logger.info('Purging queue: {queue}'.format(queue=queue_name))
        response = client.get_queue_url(QueueName=queue_name)

        queue_url = response.get('QueueUrl')
        if not queue_url:
            raise RuntimeError("No QueueUrl in the response, response: %r" % response)

        client.purge_queue(QueueUrl=queue_url)
        purged.append(queue_name)

    return {'purged': purged}
