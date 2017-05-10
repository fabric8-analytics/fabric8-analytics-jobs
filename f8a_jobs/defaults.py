#!/usr/bin/env python3
import os

_BAYESIAN_JOBS_DIR = os.path.dirname(os.path.realpath(__file__))

DEFAULT_SERVICE_PORT = 34000
SWAGGER_YAML_PATH = os.path.join(_BAYESIAN_JOBS_DIR, 'swagger.yaml')
DEFAULT_JOB_DIR = os.path.join(_BAYESIAN_JOBS_DIR, 'default_jobs')
