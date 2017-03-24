#!/usr/bin/env python3
import os
import connexion
import logging
from flask import redirect
from flask_script import Manager
from bayesian_jobs.scheduler import Scheduler
import bayesian_jobs.defaults as defaults


logger = logging.getLogger(__name__)
app = connexion.App(__name__)
app.add_api(defaults.SWAGGER_YAML_PATH)
# Expose for uWSGI
application = app.app
manager = Manager(app.app)


def init_logger():
    if not app.app.debug:
        """ Initialize Flask logging """
        handler = logging.StreamHandler()
        handler.setLevel(logging.WARNING)
        # Use flask App instead of Connexion's one
        app.app.logger.addHandler(handler)


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
        processes=1
    )

if __name__ == '__main__':
    init_logger()
    manager.run()
