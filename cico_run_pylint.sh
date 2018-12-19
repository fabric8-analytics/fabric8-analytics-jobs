#!/bin/bash

set -ex

prep() {
    yum -y update
    yum -y install epel-release
    yum -y install python34 python34-virtualenv which
}

prep
./detect-common-errors.sh
./detect-dead-code.sh
# enable when the last remaining issue will be solved
# https://fabric8-analytics.github.io/dashboard/fabric8-analytics-jobs.cc.D.html
# ./measure-cyclomatic-complexity.sh --fail-on-error
./measure-maintainability-index.sh --fail-on-error
./run-linter.sh
