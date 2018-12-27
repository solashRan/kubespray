#!/usr/bin/env bash

set -ex

pipenv --two install -r requirements.txt
pipenv run ./run_tools.py prepare $@
pipenv run ansible-playbook -i inventory/igz/hosts.ini cluster.yml -u iguazio -b --skip -tags=igz-online
pipenv run ./run_tools.py post $@
