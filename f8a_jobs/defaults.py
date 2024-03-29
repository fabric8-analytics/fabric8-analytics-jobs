#!/usr/bin/env python3

"""Module that contains global variables with the project runtime configuration."""

import os
from datetime import timedelta

_BAYESIAN_JOBS_DIR = os.path.dirname(os.path.realpath(__file__))

DEFAULT_SERVICE_PORT = 34000
SWAGGER_YAML_PATH = os.path.join(_BAYESIAN_JOBS_DIR, 'swagger.yaml')
SWAGGER_INGESTION_YAML_PATH = os.path.join(_BAYESIAN_JOBS_DIR, 'api_spec.yaml')
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
TOKEN_AUTHENTICATION = os.getenv('TOKEN_AUTHENTICATION', 'true') in ('1', 'True', 'true')
SERVICE_ACCOUNT_CLIENT_ID = os.getenv('SERVICE_ACCOUNT_CLIENT_ID', 'not-set')

BAYESIAN_DATA_IMPORTER_SERVICE_PORT = os.getenv(
    "BAYESIAN_DATA_IMPORTER_SERVICE_PORT", 9192)

BAYESIAN_DATA_IMPORTER_SERVICE_HOST = os.getenv(
    "BAYESIAN_DATA_IMPORTER_SERVICE_HOST", "data-model-importer")

DATA_IMPORTER_ENDPOINT = "http://%s:%s" % (
    BAYESIAN_DATA_IMPORTER_SERVICE_HOST,
    BAYESIAN_DATA_IMPORTER_SERVICE_PORT)

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

USER_CACHE_DIR = os.environ.get("USER_CACHE_DIR")
GEMINI_API_URL = "http://{host}:{port}/api/v1/pgsql".format(
    host=os.environ.get("GEMINI_SERVICE_HOST", "f8a-gemini-server"),
    port=os.environ.get("GEMINI_SERVICE_PORT", "5000"))
ENABLE_USER_CACHING = os.environ.get('ENABLE_USER_CACHING', 'true') == 'true'
ACCOUNT_SECRET_KEY = os.getenv('THREESCALE_ACCOUNT_SECRET', 'not-set')
