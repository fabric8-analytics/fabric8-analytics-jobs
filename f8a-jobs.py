#!/usr/bin/env python3
import os
import json
import connexion
import logging
from flask import redirect
from datetime import datetime
from flask_script import Manager
from f8a_jobs.scheduler import Scheduler
import f8a_jobs.defaults as defaults

logger = logging.getLogger(__name__)


class SafeJSONEncoder(json.JSONEncoder):
    """ Convert objects to JSON, safely """
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        try:
            return json.JSONEncoder.default(self, o)
        except:
            return repr(o)


def init_logging():
    """ Initialize application logging """
    # Initialize flask logging
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARNING)
    handler.setFormatter(formatter)
    # Use flask App instead of Connexion's one
    app.app.logger.addHandler(handler)
    # API logger
    logger.setLevel(logging.DEBUG)
    # lib logger
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    liblog = logging.getLogger('f8a_jobs')
    liblog.setLevel(logging.DEBUG)
    liblog.addHandler(handler)


app = connexion.App(__name__)
init_logging()
app.add_api(defaults.SWAGGER_YAML_PATH)
# Expose for uWSGI
application = app.app
application.json_encoder = SafeJSONEncoder
manager = Manager(app.app)


@app.route('/')
def base_url():
    # Be nice with user access
    return redirect('api/v1/ui')


@manager.command
def initjobs():
    """ initialize default jobs """""
    logger.debug("Initializing default jobs")
    Scheduler.register_default_jobs(defaults.DEFAULT_JOB_DIR)
    logger.debug("Default jobs initialized")


@manager.command
def runserver():
    """ run job service server """""
    #
    # The Flasks's runserver command was overwritten because we are using connexion.
    #
    # Make sure that you do not run the application with multiple processes since we would
    # have multiple scheduler instances. If you would like to do so, just create one scheduler
    # that would serve jobs and per-process scheduler would be in paused mode just for creating/listing jobs.
    #
    app.run(
        port=os.environ.get('JOB_SERVICE_PORT', defaults.DEFAULT_SERVICE_PORT),
        server='flask',
        debug=True,
        use_reloader=True,
        threaded=True,
        json_encoder=SafeJSONEncoder,
        processes=1
    )

if __name__ == '__main__':
    manager.run()
