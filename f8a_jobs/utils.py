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
    """Get string representation of service state/scheduler."""
    if scheduler.state == STATE_RUNNING:
        return 'running'
    elif scheduler.state == STATE_STOPPED:
        return 'stopped'
    else:
        return 'paused'


def get_job_state_str(job):
    """Get string representation of a job."""
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
    """Return a dictionary for the given job that is JSON serializable."""
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
    """Verify authentication token sent in header.

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
    """Check that a user is a member of organization.

    :param user_data: user OAuth data
    :return: True if user is a member of organization
    """
    data = requests.get(user_data['organizations_url'], params={'access_token': get_gh_token()})
    data.raise_for_status()
    return any(org_def['login'] == configuration.AUTH_ORGANIZATION for org_def in data.json())


def get_gh_token():
    return random.choice(configuration.GITHUB_ACCESS_TOKENS).strip()


def _get_queues(client):
    """List all queues in the deployment.

    :param client: AWS client instance
    :return: a dict containing mapping from queue name to queue url
    """
    response = client.list_queues(QueueNamePrefix=configuration.DEPLOYMENT_PREFIX)
    if not response or not response.get('QueueUrls'):
        raise RuntimeError("No queues in AWS response: %s" % response)

    result = {}
    for queue_url in response['QueueUrls']:
        queue_name = queue_url.rsplit('/', 1)[-1]
        result[queue_name] = queue_url

    return result


def requires_aws_sqs_access(func):
    """Return decorator to request AWS client instance and perform basic AWS config checks."""
    def wrapper(*args, **kwargs):
        if not configuration.AWS_ACCESS_KEY_ID or not configuration.AWS_SECRET_ACCESS_KEY:
            raise ValueError('Missing AWS credentials')

        client = boto3.client('sqs',
                              aws_access_key_id=configuration.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=configuration.AWS_SECRET_ACCESS_KEY,
                              region_name=configuration.AWS_SQS_REGION)
        func(client, *args, **kwargs)

    return wrapper


@requires_aws_sqs_access
def construct_queue_attributes(client):
    """Retrieve relevant attributes about queues in the given deployment."""
    queues = _get_queues(client)
    result = {}
    for queue_name, queue_url in queues.items():
        queue_info = client.get_queue_attributes(QueueUrl=queue_url,
                                                 AttributeNames=[
                                                     'ApproximateNumberOfMessages'
                                                 ])
        result[queue_name] = queue_info.pop('Attributes', {})

        if 'ApproximateNumberOfMessages' in result[queue_name]:
            number_of_messages = result[queue_name]['ApproximateNumberOfMessages']
            result[queue_name]['ApproximateNumberOfMessages'] = int(number_of_messages)

    return result


@requires_aws_sqs_access
def purge_queues(client, queues):
    """Purge given SQS queues.

    :param client: AWS client instance
    :param queues: a list of queues to be purged or star to clean all queues
    :type queues: list
    """
    purged = []
    if len(queues) == 1 and queues[0] == '*':
        queues = _get_queues(client)
        logger.debug("Cleaning all queues on AWS: {}".format(list(queues.values())))
        for queue_url, queue_name in queues.items():
            logger.info('Purging queue: {queue}'.format(queue=queue_name))
            client.purge_queue(QueueUrl=queue_url)
            purged.append(queue_name)
    else:
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
