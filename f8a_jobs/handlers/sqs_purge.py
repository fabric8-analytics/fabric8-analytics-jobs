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
                              aws_secret_access_key=aws_secret_access_key,
                              region_name='us-east-1')

        for queue in queues:
            prefix = os.environ.get('DEPLOYMENT_PREFIX')
            queue_name = '{prefix}_{queue}'.format(prefix=prefix, queue=queue)
            self.log.info('Purging queue: {queue}'.format(queue=queue_name))

            response = client.get_queue_url(QueueName=queue_name)

            queue_url = response.get('QueueUrl')
            if not queue_url:
                raise RuntimeError("No QueueUrl in the response, response: %r" % response)

            client.purge_queue(QueueUrl=queue_url)
