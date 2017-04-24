#!/usr/bin/env python3

import logging
from selinon import run_flow
from selinon import run_flow_selective
from selinon import StoragePool
from cucoslib.setup_celery import init_celery
import mosql.query as mosql_query
from mosql.util import raw as mosql_raw
from mosql.query import select


class BaseHandler(object):
    """ Base handler class for user defined handlers"""

    _DEFAULT_FILTER_TABLE_NAME = 'worker_results'
    DEFAULT_FILTER_KEY = '$filter'
    _initialized_celery = False

    def __init__(self, job_id):
        self.log = logging.getLogger(__name__)
        self.job_id = job_id
        # initialize always as the assumption is that we will use it
        self._init_celery()
        self.postgres = StoragePool.get_connected_storage('BayesianPostgres')

    @staticmethod
    def _expand_join(join_definition):
        """ Expand join definition to `join' call """
        join_table_name = join_definition.pop('table')
        join_func = getattr(mosql_query, join_definition.pop('join_type', 'join'))
        return join_func(join_table_name, **join_definition)

    def construct_select_query(self, filter_definition):
        """ Return SELECT statement that will be used as a filter

        :param filter_definition: definition of a filter that should be used for SELECT construction
        :return:
        """
        table_name = filter_definition.pop('table', self._DEFAULT_FILTER_TABLE_NAME)
        distinct = filter_definition.pop('distinct', False)
        select_count = filter_definition.pop('count', False)

        if distinct and select_count:
            raise ValueError('SELECT (DISTINCT ...) is not supported')

        if select_count and 'select' in filter_definition:
            raise ValueError('SELECT COUNT(columns) is not supported')

        if 'joins' in filter_definition:
            join_definitions = filter_definition.pop('joins')

            if type(join_definitions) not in (tuple, list):
                join_definitions = (join_definitions,)

            filter_definition['joins'] = []
            for join_def in join_definitions:
                filter_definition['joins'].append(self._expand_join(join_def))

        if 'where' in filter_definition:
            for key, value in filter_definition['where'].items():
                if self.is_filter_query(value):
                    # We can do it recursively here
                    sub_query = value.pop(self.DEFAULT_FILTER_KEY)
                    if value:
                        self.log.warning("Ignoring sub-query parameters: %s", value)
                    filter_definition['where'][key] = mosql_raw('( {} )'.format(self.construct_select_query(sub_query)))

        raw_select = select(table_name, **filter_definition)

        if distinct:
            # Note that we want to limit replace to the current SELECT, not affect nested ones
            raw_select = raw_select.replace('SELECT', 'SELECT DISTINCT', 1)
        if select_count:
            # Note that we want to limit replace to the current SELECT, not affect nested ones
            raw_select = raw_select.replace('SELECT *', 'SELECT COUNT(*)', 1)

        return raw_select

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

        if self.job_id:
            node_args['job_id'] = self.job_id

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
        return run_flow_selective(flow_name, task_names, node_args, follow_subflows, run_subsequent)

    def is_filter_query(self, filter_query):
        """
        :param filter_query: dictionary to be checked for filter_query
        :return: True if filter_query is considered to be expanded based on database query
        """
        return isinstance(filter_query, dict) and self.DEFAULT_FILTER_KEY in filter_query.keys()

    def expand_filter_query(self, filter_definition):
        """ Expand filter arguments and perform database query

        :param filter_definition:
        :return: expanded filter arguments
        """
        select_statement = self.construct_select_query(filter_definition.pop(self.DEFAULT_FILTER_KEY))
        query_result = self.postgres.session.execute(select_statement).fetchall()

        result = []
        for r in query_result:
            # Convert RowResult to key-value pair
            record = dict(r)
            # Add additional parameters that were supplied besides $filter expansion
            record.update(filter_definition)
            result.append(record)

        return result

    def execute(self, **kwargs):
        """ User defined job handler implementation """
        raise NotImplementedError()
