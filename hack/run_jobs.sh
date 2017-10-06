#!/usr/bin/env bash

set -ex

f8a-jobs.py initjobs
cd /usr/bin/
exec uwsgi --http 0.0.0.0:34000 -p 1 -w f8a-jobs --enable-threads
