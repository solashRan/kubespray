#!/usr/bin/env bash

set -ex

pipenv --two install -r requirements.txt
pipenv --two run ./run.py $@
