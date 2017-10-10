import boto3
import os

from f8a_jobs.handlers.base import BaseHandler


class SQSPurge(BaseHandler):

    def execute(self, queues):
        """ Purge given SQS queues.

        :param queues: str, space-separated list of queues to purge,
                            without deployment prefix
        """
        queues = queues.split()

        aws_access_key_id = os.environ.get('AWS_SQS_ACCESS_KEY_ID')
        aws_secret_access_key = os.environ.get('AWS_SQS_SECRET_ACCESS_KEY')

        if not aws_access_key_id or not aws_secret_access_key:
            raise ValueError('Missing AWS credentials')

        client = boto3.client('sqs', aws_access_key_id=aws_access_key_id,
                              aws_secret_access_key=aws_secret_access_key)

        for queue in queues:
            prefix = os.environ.get('DEPLOYMENT_PREFIX')
            queue_name = '{prefix}_{queue}'.format(prefix=prefix, queue=queue)
            self.log.info('Purging queue: {queue}'.format(queue=queue_name))
            client.purge_queue(QueueUrl=queue_name)
