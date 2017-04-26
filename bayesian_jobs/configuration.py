#!/usr/bin/env python3
import os
from datetime import timedelta

_BAYESIAN_JOBS_DIR = os.path.dirname(os.path.realpath(__file__))

DEFAULT_SERVICE_PORT = 34000
SWAGGER_YAML_PATH = os.path.join(_BAYESIAN_JOBS_DIR, 'swagger.yaml')
DEFAULT_JOB_DIR = os.path.join(_BAYESIAN_JOBS_DIR, 'default_jobs')
TOKEN_VALID_TIME = timedelta(days=14)
AUTH_ORGANIZATION = 'baytemp'
DISABLE_AUTHENTICATION = bool(os.environ.get('DISABLE_AUTHENTICATION', False))
GITHUB_CONSUMER_KEY = os.environ.get('GITHUB_CONSUMER_KEY', '96d6ad4971dfec52cd7c')
GITHUB_CONSUMER_SECRET = os.environ.get('GITHUB_CONSUMER_SECRET', '97a65e9066a9e4468a9a024a25073ea6e10e8ab6')
GITHUB_ACCESS_TOKEN = os.environ.get('GITHUB_ACCESS_TOKEN', '2ba44d20f2da859184b8ab11460952d49cbde32a')
APP_SECRET_KEY = os.environ.get('APP_SECRET_KEY', 'euYu3Ma6AhV7ieshOen4neigluL9aith')
