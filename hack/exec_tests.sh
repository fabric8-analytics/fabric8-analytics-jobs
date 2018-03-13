#!/usr/bin/bash

set -e
DIR=$(dirname "${BASH_SOURCE[0]}")

#validate swagger.yaml 
echo "Validating swagger.yaml"
prance validate /f8a_jobs/f8a_jobs/swagger.yaml || { echo 'Swagger.yaml validation failed' ; exit 1; }

# we need no:cacheprovider, otherwise pytest will try to write to directory .cache which is in /usr under unprivileged
# user and will cause exception
py.test -p no:cacheprovider --cov=/f8a_jobs/f8a_jobs/ --cov-report term-missing -vv $@
