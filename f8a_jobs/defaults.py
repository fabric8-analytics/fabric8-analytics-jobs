#!/usr/bin/env python3

"""Module that contains global variables with the project runtime configuration."""

import os
from datetime import timedelta

_BAYESIAN_JOBS_DIR = os.path.dirname(os.path.realpath(__file__))

DEFAULT_SERVICE_PORT = 34000
SWAGGER_YAML_PATH = os.path.join(_BAYESIAN_JOBS_DIR, 'swagger.yaml')
DEFAULT_JOB_DIR = os.path.join(_BAYESIAN_JOBS_DIR, 'default_jobs')
TOKEN_VALID_TIME = timedelta(days=14)
AUTH_ORGANIZATION = os.getenv('AUTH_ORGANIZATION', 'fabric8-analytics')
GITHUB_CONSUMER_KEY = os.getenv('GITHUB_CONSUMER_KEY', 'not-set')
GITHUB_CONSUMER_SECRET = os.getenv('GITHUB_CONSUMER_SECRET', 'not-set')
GITHUB_ACCESS_TOKENS = os.getenv('GITHUB_ACCESS_TOKENS', '').split(',')
APP_SECRET_KEY = os.getenv('APP_SECRET_KEY', 'not-set')
AWS_ACCESS_KEY_ID = os.getenv('AWS_SQS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SQS_SECRET_ACCESS_KEY')
AWS_SQS_REGION = os.getenv('AWS_SQS_REGION', 'us-east-1')
DEPLOYMENT_PREFIX = os.getenv('DEPLOYMENT_PREFIX', os.getenv('USER'))

# keep disabled authentication by default
DISABLE_AUTHENTICATION = os.getenv('DISABLE_AUTHENTICATION', '1') in ('1', 'True', 'true')
