#!/usr/bin/env bash

set -ex

pipenv install -r requirements.txt
pipenv run ./run.py $@
