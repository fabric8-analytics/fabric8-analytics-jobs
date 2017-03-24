from .base import BaseHandler


class SelectiveFlowScheduling(BaseHandler):
    """ Schedule multiple selective flows of a type """
    def execute(self, flow_name, task_names, flow_arguments, follow_subflows=True, run_subsequent=False):
        """ Schedule a selective flow

        :param flow_name: Selinon flow name that should be scheduled
        :param task_names: a list of tasks that should be executed
        :param flow_arguments: a list of flow arguments for which we are scheduling selective flows
        :param follow_subflows: follow subflows when resolving tasks to be executed
        :param run_subsequent: run tasks that follow after desired tasks stated in task_names
        """
        for node_args in flow_arguments:
            if self.job_id:
                node_args['job_id'] = self.job_id
            self.run_selinon_flow_selective(flow_name, task_names, node_args, follow_subflows, run_subsequent)
