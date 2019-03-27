#!/usr/bin/bash

# test coverage threshold
COVERAGE_THRESHOLD=15

# this script is copied by CI, we don't need it
rm -f env-toolkit

set -e
DIR=$(dirname "${BASH_SOURCE[0]}")

pushd /f8a_jobs

echo "*****************************************"
echo "*** Cyclomatic complexity measurement ***"
echo "*****************************************"
radon cc -s -a -i venv .

echo "*****************************************"
echo "*** Maintainability Index measurement ***"
echo "*****************************************"
radon mi -s -i venv .

popd

echo "*****************************************"
echo "*** Unit tests ***"
echo "*****************************************"
# we need no:cacheprovider, otherwise pytest will try to write to directory .cache which is in /usr under unprivileged
# user and will cause exception
py.test -p no:cacheprovider --cov=/f8a_jobs/f8a_jobs/ --cov-report term-missing --cov-fail-under=$COVERAGE_THRESHOLD -vv $@

codecov --token=1fb5003d-7ea0-4487-8397-139ab1314b4b
