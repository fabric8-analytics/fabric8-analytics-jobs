#!/usr/bin/bash

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
py.test -p no:cacheprovider --cov=/f8a_jobs/f8a_jobs/ --cov-report term-missing -vv $@
