#!/usr/bin/env python3

import logging
import abc
from selinon import run_flow
from selinon import run_flow_selective
from cucoslib.setup_celery import init_celery


class BaseHandler(metaclass=abc.ABCMeta):
    """ Base handler class for user defined handlers"""
    _initialized_celery = False

    def __init__(self, job_id):
        self.log = logging.getLogger(self.__class__.__name__)
        self.job_id = job_id

    def _init_celery(self):
        """ Initialize celery and connect to the broker """
        if not self._initialized_celery:
            init_celery(result_backend=False)
            self._initialized_celery = True

    def run_selinon_flow(self, flow_name, node_args):
        """Connect to broker, if not connected, and run Selinon flow

        :param flow_name: flow that should be run
        :param node_args: flow arguments
        """
        self.log.debug("Scheduling Selinon flow '%s' with node_args: '%s'", flow_name, node_args)
        self._init_celery()
        return run_flow(flow_name, node_args)

    def run_selinon_flow_selective(self, flow_name, task_names, node_args, follow_subflows, run_subsequent):
        """Connect to broker, if not connected, and run Selinon selective flow

        :param flow_name: flow that should be run
        :param task_names: a list of tasks that should be executed
        :param node_args: flow arguments
        :param follow_subflows: follow subflows when resolving tasks to be executed
        :param run_subsequent: run tasks that follow after desired tasks stated in task_names
        """
        self.log.debug("Scheduling selective Selinon flow '%s' with node_args: '%s'", flow_name, node_args)
        self._init_celery()
        return run_flow_selective(flow_name, task_names, node_args, follow_subflows, run_subsequent)

    @abc.abstractmethod
    def execute(self, **kwargs):
        """ User defined job handler implementation """
        raise NotImplementedError()
