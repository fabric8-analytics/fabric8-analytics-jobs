#!/usr/bin/env bash

set -ex
# As in worker, we need inject environment setup
DIR=$(dirname "${BASH_SOURCE[0]}")
source $DIR/env.sh

bayesian-jobs.py initjobs
cd /usr/bin/
exec uwsgi --http 0.0.0.0:34000 -p 1 -w bayesian-jobs --enable-threads
