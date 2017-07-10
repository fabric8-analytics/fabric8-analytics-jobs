#!/usr/bin/env python3
import os
from datetime import timedelta

_BAYESIAN_JOBS_DIR = os.path.dirname(os.path.realpath(__file__))

DEFAULT_SERVICE_PORT = 34000
SWAGGER_YAML_PATH = os.path.join(_BAYESIAN_JOBS_DIR, 'swagger.yaml')
DEFAULT_JOB_DIR = os.path.join(_BAYESIAN_JOBS_DIR, 'default_jobs')
TOKEN_VALID_TIME = timedelta(days=14)
AUTH_ORGANIZATION = 'fabric8-analytics'
DISABLE_AUTHENTICATION = bool(os.environ.get('DISABLE_AUTHENTICATION', False))
GITHUB_CONSUMER_KEY = os.environ.get('GITHUB_CONSUMER_KEY', '')
GITHUB_CONSUMER_SECRET = os.environ.get('GITHUB_CONSUMER_SECRET', '')
GITHUB_ACCESS_TOKEN = os.environ.get('GITHUB_ACCESS_TOKEN', '')
APP_SECRET_KEY = os.environ.get('APP_SECRET_KEY', '')
