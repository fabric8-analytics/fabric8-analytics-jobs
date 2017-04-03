from .base import BaseHandler


class SelectiveFlowScheduling(BaseHandler):
    """ Schedule multiple selective flows of a type """
    def execute(self, flow_name, task_names, flow_arguments, follow_subflows=True, run_subsequent=False):
        """ Schedule a selective flow, do filter expansion if needed

        :param flow_name: Selinon flow name that should be scheduled
        :param task_names: a list of tasks that should be executed
        :param flow_arguments: a list of flow arguments for which we are scheduling selective flows
        :param follow_subflows: follow subflows when resolving tasks to be executed
        :param run_subsequent: run tasks that follow after desired tasks stated in task_names
        """
        for node_args in flow_arguments:
            if self.is_filter_query(node_args):
                for args in self.expand_filter_query(node_args):
                    self.run_selinon_flow_selective(flow_name, task_names, args, follow_subflows, run_subsequent)
            else:
                self.run_selinon_flow_selective(flow_name, task_names, node_args, follow_subflows, run_subsequent)
