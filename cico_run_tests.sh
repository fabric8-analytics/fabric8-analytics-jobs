#!/bin/bash

set -ex

. cico_setup.sh

build_image

make test

push_image
