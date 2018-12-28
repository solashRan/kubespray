#!/usr/bin/env bash

set -ex

./gen_templates.py $@
ansible-playbook -i inventory/igz/hosts.ini cluster.yml -u iguazio -b --skip -tags=igz-online
