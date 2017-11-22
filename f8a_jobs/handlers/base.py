#!/usr/bin/env python3

import logging
import copy
from collections import namedtuple
from json2sql import select2sql
from json2sql.select import DEFAULT_FILTER_KEY
from selinon import run_flow
from selinon import run_flow_selective
from selinon import StoragePool
from f8a_worker.setup_celery import init_celery
from sqlalchemy.exc import SQLAlchemyError

CountRange = namedtuple('CountRange', ['min', 'max'])


class BaseHandler(object):
    """Base handler class for user defined handlers."""

    _initialized_celery = False

    def __init__(self, job_id):
        self.log = logging.getLogger(__name__)
        self.job_id = job_id
        # initialize always as the assumption is that we will use it
        self._init_celery()
        self.postgres = StoragePool.get_connected_storage('BayesianPostgres')

    @staticmethod
    def construct_select_query(filter_definition):
        """Return SELECT statement that will be used as a filter.

        :param filter_definition: definition of a filter that should be used
        for SELECT construction
        :return:
        """
        return select2sql(filter_definition)

    def _init_celery(self):
        """Initialize celery and connect to the broker."""
        if not self._initialized_celery:
            init_celery(result_backend=False)
            self._initialized_celery = True

    def run_selinon_flow(self, flow_name, node_args):
        """Connect to broker, if not connected, and run Selinon flow.

        :param flow_name: flow that should be run
        :param node_args: flow arguments
        """
        self.log.debug("Scheduling Selinon flow '%s' with node_args: '%s', job '%s'",
                       flow_name, node_args, self.job_id)

        if self.job_id:
            node_args['job_id'] = self.job_id

        return run_flow(flow_name, node_args)

    def run_selinon_flow_selective(self, flow_name, task_names, node_args, follow_subflows,
                                   run_subsequent):
        """Connect to broker, if not connected, and run Selinon selective flow.

        :param flow_name: flow that should be run
        :param task_names: a list of tasks that should be executed
        :param node_args: flow arguments
        :param follow_subflows: follow subflows when resolving tasks to be executed
        :param run_subsequent: run tasks that follow after desired tasks stated in task_names
        """
        if flow_name in ('bayesianFlow', 'bayesianAnalysisFlow'):
            task_names = list(set(task_names) | {'FinalizeTask', 'ResultCollector',
                                                 'GraphImporterTask'})

        if flow_name in ('bayesianPackageFlow', 'bayesianPackageAnalysisFlow'):
            task_names = list(set(task_names) | {'PackageFinalizeTask', 'PackageResultCollector',
                                                 'PackageGraphImporterTask'})

        self.log.debug("Scheduling selective Selinon flow '%s' with tasks '%s' and node_args: "
                       "'%s', job '%s'", flow_name, task_names, node_args, self.job_id)
        return run_flow_selective(flow_name, task_names, node_args, follow_subflows,
                                  run_subsequent)

    def is_filter_query(self, filter_query):
        """
        :param filter_query: dictionary to be checked for filter_query
        :return: True if filter_query is considered to be expanded based on database query
        """
        return isinstance(filter_query, dict) and DEFAULT_FILTER_KEY in filter_query.keys()

    def expand_filter_query(self, filter_definition):
        """Expand filter arguments and perform database query.

        :param filter_definition:
        :return: expanded filter arguments
        """
        # As filters of periodic jobs are stored in memory, copy filter
        # definition so the original is not overwritten
        filter_definition = copy.deepcopy(filter_definition)
        select_statement = self.construct_select_query(
            filter_definition.pop(DEFAULT_FILTER_KEY))
        try:
            query_result = self.postgres.session.execute(select_statement).fetchall()
        except SQLAlchemyError:
            self.postgres.session.rollback()
            raise

        result = []
        for r in query_result:
            # Convert RowResult to key-value pair
            record = dict(r)
            # Add additional parameters that were supplied besides $filter expansion
            record.update(filter_definition)
            result.append(record)

        return result

    def execute(self, **kwargs):
        """User defined job handler implementation."""
        raise NotImplementedError()


class AnalysesBaseHandler(BaseHandler):
    """Base handler for specific analyses handlers."""

    _DEFAULT_COUNT = 1000
    _DEFAULT_NVERSIONS = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nversions = self._DEFAULT_NVERSIONS
        self.popular = True
        self.count = CountRange(min=1, max=self._DEFAULT_COUNT)
        self.force = False
        self.recursive_limit = None
        self.force_graph_sync = False
        self.ecosystem = None

    @staticmethod
    def ecosystem2handler_name(ecosystem):
        """Convert ecosystem name to handler class name.

        :param ecosystem: name ecosystem
        :return: name of handler class
        """
        # avoid cyclic imports
        from . import (MavenPopularAnalyses, NpmPopularAnalyses, PythonPopularAnalyses,
                       NugetPopularAnalyses, GolangPopularAnalyses)

        if ecosystem == 'maven':
            return MavenPopularAnalyses.__name__
        elif ecosystem == 'npm':
            return NpmPopularAnalyses.__name__
        elif ecosystem == 'pypi':
            return PythonPopularAnalyses.__name__
        elif ecosystem == 'nuget':
            return NugetPopularAnalyses.__name__
        elif ecosystem == 'go':
            return GolangPopularAnalyses.__name__

        raise ValueError("Unregistered handler for ecosystem '{}'".format(ecosystem))

    def analyses_selinon_flow(self, name, version):
        """Run Selinon flow for analyses.

        :param name: name of the package to analyse
        :param version: package version
        :return: dispatcher ID serving flow
        """
        node_args = {
            'ecosystem': self.ecosystem,
            'name': name,
            'version': version,
            'force': self.force,
            'force_graph_sync': self.force_graph_sync
        }

        if self.recursive_limit is not None:
            node_args['recursive_limit'] = self.recursive_limit

        self.log.debug("Scheduling %s/%s" % (name, version))
        return self.run_selinon_flow('bayesianFlow', node_args)

    @classmethod
    def _parse_count(cls, count=None):
        """Parse count string.

        :param count: string count representation
        :rtype: CountRange
        :raises ValueError: bad count provided
        """
        count = count or str(cls._DEFAULT_COUNT)
        count = sorted(map(int, count.split("-")))

        if len(count) == 1:
            count = CountRange(min=1, max=count[0])
        elif len(count) == 2:
            count = CountRange(min=count[0], max=count[1])
            if count.min >= count.max:
                raise ValueError("Bad count %r" % count)

        if len(count) not in (1, 2) or count.min < 0 or count.max < 0:
            raise ValueError("Bad count %r" % count)

        return count

    @classmethod
    def check_arguments(cls, **kwargs):
        """Check provided arguments.

        :param kwargs: analyses keyword arguments as passed to endpoint
        """
        # type checks are transparently done by Swagger
        # try to parse count
        if kwargs.get('count') is not None:
            cls._parse_count(kwargs['count'])
        # is ecosystem handler registered?
        cls.ecosystem2handler_name(kwargs.get('ecosystem'))
        # non-negative limit
        if kwargs.get('recursive_limit') is not None and kwargs['recursive_limit'] < 0:
            raise ValueError("Unable to use negative recursive limit")

    def execute(self, ecosystem, popular=True, count=None, nversions=None,
                force=False, recursive_limit=None, force_graph_sync=False):
        """Run analyses on maven projects.

        :param ecosystem: ecosystem name
        :param popular: boolean, sort index by popularity
        :param count: str, number or range of projects to analyse
        :param nversions: how many latest versions of a project to schedule
        :param force: force analyses scheduling
        :param recursive_limit: number of analyses done transitively
        :param force_graph_sync: force sync to graph DB
        """
        self.count = self._parse_count(count)
        self.ecosystem = ecosystem
        self.nversions = nversions or self._DEFAULT_NVERSIONS
        self.force = force
        self.recursive_limit = recursive_limit
        self.force_graph_sync = force_graph_sync

        return self.do_execute(popular)

    def do_execute(self, popular=True):
        """Ecosystem specific analyses handler."""
        raise NotImplementedError()
