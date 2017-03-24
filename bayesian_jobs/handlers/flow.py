from .base import BaseHandler


class FlowScheduling(BaseHandler):
    """ Schedule multiple flows of a type """
    def execute(self, flow_name, flow_arguments):
        """Schedule multiple flows of a type

        :param flow_name: flow name that should be scheduled
        :param flow_arguments: a list of flow arguments per flow
        """
        for node_args in flow_arguments:
            if self.job_id:
                node_args['job_id'] = self.job_id
            self.run_selinon_flow(flow_name, node_args)
