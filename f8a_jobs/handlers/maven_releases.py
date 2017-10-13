import os

from f8a_worker.utils import cwd
from f8a_worker.utils import TimedCommand
from f8a_worker.utils import tempdir
from selinon import StoragePool

from .base import BaseHandler


class MavenReleasesAnalyses(BaseHandler):
    """Trigger analysis of newly released maven packages."""

    def execute(self):
        self.log.info("Checking maven index for new releases")
        maven_index_checker_dir = os.getenv('MAVEN_INDEX_CHECKER_PATH')
        target_dir = os.path.join(maven_index_checker_dir, 'target')
        central_index_dir = os.path.join(target_dir, 'central-index')
        timestamp_path = os.path.join(central_index_dir, 'timestamp')

        s3 = StoragePool.get_connected_storage('S3MavenIndex')
        self.log.info('Fetching pre-built maven index from S3, if available.')
        s3.retrieve_index_if_exists(target_dir)

        old_timestamp = 0
        try:
            old_timestamp = int(os.stat(timestamp_path).st_mtime)
        except OSError:
            self.log.info('Timestamp is missing, we will probably need to build the index '
                          'from scratch.')
            pass

        last_offset = s3.get_last_offset()
        with tempdir() as java_temp_dir:
            cmd = ['java', '-Xmx768m', '-Djava.io.tmpdir={}'.format(java_temp_dir),
                   '-jar', 'maven-index-checker.jar', '-c']

            with cwd(maven_index_checker_dir):
                output = TimedCommand.get_command_output(cmd, is_json=True, graceful=False,
                                                         timeout=1200)

                new_timestamp = int(os.stat(timestamp_path).st_mtime)
                if old_timestamp != new_timestamp:
                    self.log.info('Storing pre-built maven index to S3...')
                    s3.store_index(target_dir)
                    self.log.debug('Stored. Index in S3 is up-to-date.')
                else:
                    self.log.info('Index in S3 is up-to-date.')

                current_count = output['count']
                self.log.debug("Number of entries in maven indexer: %d, "
                               "last offset used: %d", current_count, last_offset)
                to_schedule_count = current_count - last_offset
                if to_schedule_count == 0:
                    self.log.info("No new packages to schedule, exiting...")
                    return

                cmd = ['java', '-Xmx768m',
                       '-Djava.io.tmpdir={}'.format(java_temp_dir),
                       '-jar', 'maven-index-checker.jar',
                       '-r', '0-{}'.format(to_schedule_count)]
                output = TimedCommand.get_command_output(cmd, is_json=True, graceful=False,
                                                         timeout=1200)

                self.log.info("Found %d new packages to analyse, scheduling analyses...",
                              len(output))
                for entry in output:
                    self.run_selinon_flow('bayesianFlow', {
                        'ecosystem': 'maven',
                        'name': '{groupId}:{artifactId}'.format(**entry),
                        'version': entry['version'],
                        'recursive_limit': 0
                    })

        s3.set_last_offset(current_count)
        self.log.info("All new maven releases scheduled for analysis, exiting..")
