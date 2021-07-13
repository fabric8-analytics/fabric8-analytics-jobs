#!/usr/bin/env python3

"""Module containing handlers for REST API calls, Swagger UI etc."""

import os
import json
import connexion
import logging
from flask import redirect, jsonify
from datetime import datetime
from flask_script import Manager
from f8a_jobs.scheduler import Scheduler
import f8a_jobs.defaults as defaults

from f8a_jobs.models import create_models
from f8a_jobs.auth import oauth

from raven.contrib.flask import Sentry
from werkzeug.contrib.fixers import ProxyFix
from f8a_worker.setup_celery import init_celery, init_selinon
from f8a_jobs import user_cache


class SafeJSONEncoder(json.JSONEncoder):
    """Convert objects to JSON, safely."""

    def default(self, o):
        """Override the base class method to work with datetimes properly."""
        if isinstance(o, datetime):
            return o.isoformat()
        try:
            return json.JSONEncoder.default(self, o)
        except TypeError:
            return repr(o)


def init_logging(logger):
    """Initialize application logging."""
    # Initialize flask logging
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARNING)
    handler.setFormatter(formatter)
    # Use flask App instead of Connexion's one
    application.logger.addHandler(handler)
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
app.app.wsgi_app = ProxyFix(app.app.wsgi_app)
sentry = Sentry(app.app, dsn=defaults.SENTRY_DSN, logging=True, level=logging.ERROR)

application = app.app

# Setup Logging
logger = logging.getLogger(__name__)
init_logging(logger)

app.add_api(defaults.SWAGGER_YAML_PATH)
app.add_api(defaults.SWAGGER_INGESTION_YAML_PATH)

# Expose for uWSGI
application.json_encoder = SafeJSONEncoder
manager = Manager(application)

# Needed for session
application.secret_key = defaults.APP_SECRET_KEY
oauth.init_app(application)

# Initializing Selinon and Celery while starting the application
logger.debug("Initializing Selinon")
init_celery(result_backend=False)
init_selinon()
logger.debug("Selinon initialized successfully")


@app.route('/')
def base_url():
    """Redirect client to the Swagger UI web page."""
    # Be nice with user access
    return redirect('api/v1/ui')


@app.route('/api/v1')
def api_v1():
    """Accept and respont to all REST API calls."""
    paths = []

    for rule in application.url_map.iter_rules():
        rule = str(rule)
        if rule.startswith('/api/v1'):
            paths.append(rule)

    return jsonify({'paths': paths})


@manager.command
def initjobs():
    """Initialize default jobs."""""
    logger.debug("Initializing default jobs")
    Scheduler.register_default_jobs(defaults.DEFAULT_JOB_DIR)
    logger.debug("Default jobs initialized")
    logger.debug("Initializing DB for tokens")
    create_models()
    logger.debug("DB for tokens initialized")
    user_cache.create_cache()
    logger.debug("user cache is created")


@manager.command
def runserver():
    """Run job service server."""
    #
    # The Flasks's runserver command was overwritten because we are using connexion.
    #
    # Make sure that you do not run the application with multiple processes since we would
    # have multiple scheduler instances. If you would like to do so, just create one scheduler
    # that would serve jobs and per-process scheduler would be in paused mode
    # just for creating/listing jobs.
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
