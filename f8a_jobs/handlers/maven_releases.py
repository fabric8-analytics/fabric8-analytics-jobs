"""Trigger analysis of newly released maven packages."""

import os
import tempfile
from shutil import rmtree

from f8a_worker.utils import cwd
from f8a_worker.utils import TimedCommand
from f8a_worker.errors import TaskError
from selinon import StoragePool

from .base import BaseHandler


class MavenReleasesAnalyses(BaseHandler):
    """Trigger analysis of newly released maven packages."""

    def execute(self):
        """Start the analysis."""
        self.log.info("Checking maven index for new releases")
        maven_index_checker_dir = os.getenv('MAVEN_INDEX_CHECKER_PATH')
        maven_index_checker_data_dir = os.environ.get('MAVEN_INDEX_CHECKER_DATA_PATH',
                                                      '/tmp/index-checker')
        os.makedirs(maven_index_checker_data_dir, exist_ok=True)
        central_index_dir = os.path.join(maven_index_checker_data_dir, 'central-index')
        timestamp_path = os.path.join(central_index_dir, 'timestamp')

        s3 = StoragePool.get_connected_storage('S3MavenIndex')
        self.log.info('Fetching pre-built maven index from S3, if available.')
        s3.retrieve_index_if_exists(maven_index_checker_data_dir)

        old_timestamp = 0
        try:
            old_timestamp = int(os.stat(timestamp_path).st_mtime)
        except OSError:
            self.log.info('Timestamp is missing, we need to build the index from scratch.')
            pass

        last_offset = s3.get_last_offset()

        java_temp_dir = tempfile.mkdtemp(prefix='tmp-', dir=os.environ.get('PV_DIR', '/tmp'))

        cmd = ['java', '-Xmx768m',
               '-Djava.io.tmpdir={}'.format(java_temp_dir),
               '-DcentralIndexDir={}'.format(central_index_dir),
               '-jar', 'maven-index-checker.jar', '-c']

        with cwd(maven_index_checker_dir):
            try:
                output = TimedCommand.get_command_output(
                    cmd, is_json=True, graceful=False, timeout=3600
                )

                current_count = output['count']
                new_timestamp = int(os.stat(timestamp_path).st_mtime)
                if old_timestamp != new_timestamp:
                    self.log.info('Storing pre-built maven index to S3...')
                    s3.store_index(maven_index_checker_data_dir)
                    self.log.debug('Stored. Index in S3 is up-to-date.')
                    if old_timestamp == 0:
                        s3.set_last_offset(current_count)
                        self.log.info('This is first run, i.e. all packages are considered new. '
                                      'Skipping scheduling to not analyze all packages in index.')
                        return
                else:
                    self.log.info('Index in S3 is up-to-date.')

                self.log.debug("Number of entries in maven indexer: %d, "
                               "last offset used: %d", current_count, last_offset)
                to_schedule_count = current_count - last_offset
                if to_schedule_count == 0:
                    self.log.info("No new packages to schedule, exiting...")
                    return

                cmd = ['java', '-Xmx768m',
                       '-Djava.io.tmpdir={}'.format(java_temp_dir),
                       '-DcentralIndexDir={}'.format(central_index_dir),
                       '-jar', 'maven-index-checker.jar',
                       '-r', '0-{}'.format(to_schedule_count)]
                output = TimedCommand.get_command_output(
                    cmd, is_json=True, graceful=False, timeout=3600
                )
            except TaskError as e:
                self.log.exception(e)
                raise
            finally:
                rmtree(central_index_dir)
                self.log.debug('central-index/ deleted')
                rmtree(java_temp_dir)

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
