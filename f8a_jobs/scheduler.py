#!/usr/bin/env python3

"""Scheduler wrapper to ensure that we have a single scheduler per process."""

import os
import logging
import traceback
import yaml
import uuid
from datetime import timedelta
from datetime import datetime
from dateutil.parser import parse as parse_datetime
from pytimeparse.timeparse import timeparse
from functools import wraps
from threading import Lock
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from f8a_worker.defaults import configuration as worker_configuration
import f8a_jobs.handlers as handlers
from f8a_jobs.utils import is_failed_job_handler_name


class ScheduleJobError(Exception):
    """An exception raised on job creation error."""

    pass


class Scheduler(object):
    """Scheduler wrapper to ensure that we have a single scheduler per process."""

    _scheduler = None
    _scheduler_creation_lock = Lock()
    scheduler_lock = Lock()
    log = logging.getLogger(__name__)
    _SCHEDULER_CONF = {
        'apscheduler.jobstores.default': {
            'type': 'sqlalchemy',
            'url': worker_configuration.POSTGRES_CONNECTION
        },
        'apscheduler.executors.default': {
            'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
            'max_workers': '20'
        },
        'apscheduler.executors.processpool': {
            'type': 'processpool',
            'max_workers': '5'
        },
        'apscheduler.job_defaults.coalesce': 'true',
        'apscheduler.job_defaults.max_instances': '1',
        'apscheduler.timezone': 'UTC'
    }

    def __init__(self):
        """Raise a exception because the Scheduler class must be instantiated via factory method."""
        raise NotImplementedError()

    @classmethod
    def get_scheduler(cls):
        """Get scheduler instance.

        :return: scheduler instance
        """
        if cls._scheduler is None:
            with cls._scheduler_creation_lock:
                if cls._scheduler is None:
                    cls._scheduler = BackgroundScheduler(cls._SCHEDULER_CONF)
                    cls._scheduler.start(paused=bool(os.environ.get('JOB_SERVICE_PAUSED')))

        return cls._scheduler

    @classmethod
    def get_paused_scheduler(cls):
        """Return paused scheduler for feeding jobs.

        :return: scheduler instance
        """
        # As we would like to feed default jobs, not to run any job, make sure
        # we start scheduler in paused mode.
        if cls._scheduler is not None:
            return cls._scheduler
        else:
            scheduler = BackgroundScheduler(cls._SCHEDULER_CONF)
            scheduler.start(paused=True)
            return scheduler

    @classmethod
    def schedule_job(cls, scheduler, handler_name,
                     job_id=None, when=None, periodically=None, misfire_grace_time=None,
                     state=None, modify_existing_job=False, **kwargs):
        """Schedule a job.

        :param scheduler: scheduler that should be used to schedule a job
        :param handler_name: name of handler that is used to handle the given job
        :param job_id: unique job id, if None, job_id is generated
        :param when: date and time (string representation) when the given job should be fired
        :param periodically: string representation of the periodical execution
        (None = job will be executed only once)
        :param misfire_grace_time: time after which the given job should be
        thrown away because of misfire
        :param state: a string ('paused'/'running') representation of job state
        :param modify_existing_job: if True, existing job will be modified
        according to new job spec
        :param kwargs: handler kwargs
        :return: scheduled apscheduler.Job instance
        """
        if state not in (None, "running", "paused"):
            raise ValueError("Unknown state '%s' provided, could be 'running' or 'paused'")

        # just to be sure that the handler actually exists
        if not hasattr(handlers, handler_name):
            raise ValueError("Unknown handler '%s'" % handler_name)

        if when:
            try:
                when = parse_datetime(when)
            except ValueError as exc:
                raise ScheduleJobError("Unable to parse datetime format for 'when': '%s'" % when)\
                    from exc
            if when < datetime.now():
                raise ScheduleJobError("Cannot schedule event at '%s' to past" % str(when))

        if misfire_grace_time:
            seconds = timeparse(misfire_grace_time)

            if seconds is None:
                raise ScheduleJobError("Unable to parse format for 'misfire_grace_time': '%s'" %
                                       misfire_grace_time)

            misfire_grace_time = seconds

        if periodically:
            seconds = timeparse(periodically)

            if seconds is None:
                raise ScheduleJobError("Unable to parse format for 'periodically': '%s'" %
                                       periodically)

            trigger = 'interval'
            trigger_kwargs = {
                'seconds': seconds,
                'start_date': when
            }
        else:
            # One time job
            trigger = 'date'
            trigger_kwargs = {
                'run_date': when
            }

        if state == 'paused':
            trigger_kwargs['next_run_time'] = None

        try:
            job = scheduler.get_job(job_id)
            if modify_existing_job and job is not None:
                cls.log.info("Performing job change (if any) on already existing job '%s'", job_id)
                job.modify(
                    kwargs=kwargs or {},
                    misfire_grace_time=misfire_grace_time,
                )
                # Check for trigger configuration changes
                old_trigger = job.trigger
                trigger_change = \
                    (trigger == 'date' and not isinstance(old_trigger, DateTrigger)) or \
                    (trigger == 'interval' and not isinstance(old_trigger, IntervalTrigger))
                if not trigger_change:
                    if isinstance(old_trigger, DateTrigger) \
                            and old_trigger.run_date != when:
                        cls.log.info("Job execution has changed from %s to %s, modifying entry...",
                                     old_trigger.run_date, when)
                        job.reschedule(trigger=trigger, **trigger_kwargs)
                    elif isinstance(old_trigger, IntervalTrigger) \
                            and old_trigger.interval != timedelta(seconds=seconds):
                        cls.log.info("Job periodic interval has changed from %s to %s, "
                                     "modifying entry...",
                                     old_trigger.interval, timedelta(seconds=seconds))
                        job.reschedule(trigger=trigger, **trigger_kwargs)
                    else:
                        cls.log.info("Job execution time was left untouched - no change performed")
                else:
                    cls.log.info("Trigger type has changed, force rescheduling job")
                    job.reschedule(trigger, **trigger_kwargs)
            else:
                if not job_id:
                    # explicitly assign job id so we have this ID in logs and job is trackable
                    job_id = str(uuid.uuid4())

                # force replace existing one
                job = scheduler.add_job(
                    job_execute,
                    args=(handler_name, job_id),
                    kwargs=kwargs or {},
                    id=job_id,
                    replace_existing=True,
                    trigger=trigger,
                    misfire_grace_time=misfire_grace_time,
                    **trigger_kwargs
                )
        except Exception as e:
            cls.log.exception(str(e))
            raise ScheduleJobError("Unable to schedule job: '%s'" % str(e)) from e

        return job

    @classmethod
    def register_default_jobs(cls, job_dir):
        """Register default jobs as stated in configuration files.

        :param job_dir: directory in which the default jobs sit (YAML files)
        """
        cls.log.info("Registering default jobs")
        scheduler = cls.get_paused_scheduler()

        for job_file_basename in os.listdir(job_dir):
            cls.log.info("Processing file '%s'" % job_file_basename)
            job_file = os.path.join(job_dir, job_file_basename)

            if not os.path.isfile(job_file) or job_file_basename.startswith("."):
                cls.log.warning("Skipping file '%s'", job_file)

            with open(job_file, 'r') as f:
                job_info = yaml.load(f, Loader=yaml.SafeLoader)

            if 'handler' not in job_info:
                raise ValueError("Expected handler name under 'handler' key in file '%s'", job_file)

            if 'job_id' not in job_info:
                raise ValueError("Expected job ID under 'job_id' key in file '%s'", job_file)

            cls.log.info("Registering default job '%s'", job_info['job_id'])

            try:
                job = cls.schedule_job(scheduler, job_info.pop('handler'),
                                       modify_existing_job=True, **job_info)
                cls.log.info("Job '%s' from file '%s' successfully added", job_file, job.id)
            except ScheduleJobError as exc:
                cls.log.exception("Failed to register job from file '%s': %s", job_file, str(exc))


def job_execute(handler_name, job_id, **handler_kwargs):
    """Instantiate and run the handler.

    :param handler_name: name of the handler that should be run
    :param job_id: id of the handler that should be run
    :param handler_kwargs: handler keyword arguments
    """
    # This has to ba a function as apscheduler does not handler classmethods transparently
    handler = getattr(handlers, handler_name)
    instance = handler(job_id)

    try:
        instance.execute(**handler_kwargs)
    except Exception as exc:
        logging.exception("Job '%s' failed, registering ErrorHandler: %s", job_id, str(exc))
        if not is_failed_job_handler_name(handler_name):
            exc_traceback = traceback.format_exc()
            error_handler_kwargs = {
                'exc_str': str(exc),
                'exc_traceback': exc_traceback,
                'failed_job_id': job_id,
                'failed_job_handler': handler_name,
                'failed_handler_kwargs': handler_kwargs
            }
            Scheduler.schedule_job(Scheduler.get_paused_scheduler(), handlers.ErrorHandler.__name__,
                                   state='paused', kwargs=error_handler_kwargs)
        else:
            Scheduler.log.exception("Failed to record job failure job")
    else:
        logging.info("Job '%s' successfully finished", job_id)


def uses_scheduler(func):
    """Wrap the specified function - add a scheduler instance as a first argument."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # possible bottleneck here - I'm not sure if apscheduler implementation
        # is thread safe - suppose not
        with Scheduler.scheduler_lock:
            return func(Scheduler.get_scheduler(), *args, **kwargs)
    return wrapper
