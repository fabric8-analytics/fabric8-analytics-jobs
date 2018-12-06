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
./measure-maintainability-index.sh --fail-on-error
./run-linter.sh
