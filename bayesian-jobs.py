#!/usr/bin/env python3
import os
import json
import logging
import connexion
from datetime import datetime
from flask_script import Manager
from flask import redirect
from bayesian_jobs.scheduler import Scheduler
import bayesian_jobs.configuration as configuration
from bayesian_jobs.models import create_models
from bayesian_jobs.auth import oauth

logger = logging.getLogger(__name__)

connexion_app = connexion.App(__name__)
connexion_app.add_api(configuration.SWAGGER_YAML_PATH)
app = connexion_app.app
# Needed for sesion
app.secret_key = configuration.APP_SECRET_KEY
oauth.init_app(app)


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
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARNING)
    # Use flask App instead of Connexion's one
    app.logger.addHandler(handler)
    # API logger
    logger.setLevel(logging.DEBUG)
    # lib logger
    liblog = logging.getLogger('bayesian_jobs')
    liblog.setLevel(logging.DEBUG)
    liblog.addHandler(logging.StreamHandler())


init_logging()
# Expose for uWSGI
application = app
application.json_encoder = SafeJSONEncoder
manager = Manager(app)


@app.route('/')
def base_url():
    # Be nice with user access
    return redirect('api/v1/ui')


@manager.command
def initjobs():
    """ initialize default jobs """""
    logger.debug("Initializing default jobs")
    Scheduler.register_default_jobs(configuration.DEFAULT_JOB_DIR)
    logger.debug("Default jobs initialized")
    logger.debug("Initializing DB for tokens")
    create_models()
    logger.debug("DB for tokens initialized")


@manager.command
def runserver():
    """ run job service server """""
    #
    # The Flasks's runserver command was overwritten because we are using connexion.
    #
    # Make sure that you do not run the application with multiple processes since we would
    # have multiple scheduler instances. If you would like to do so, just create one scheduler
    # that would serve jobs and per-process scheduler would be in paused mode just for creating/listing jobs.
    app.run(
        port=os.environ.get('JOB_SERVICE_PORT', configuration.DEFAULT_SERVICE_PORT),
        server='flask',
        debug=True,
        use_reloader=True,
        threaded=True,
        json_encoder=SafeJSONEncoder,
        processes=1
    )

if __name__ == '__main__':
    manager.run()
