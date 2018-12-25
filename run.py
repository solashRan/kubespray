#!/usr/bin/env python
import sys
import json
import socket
import logging
import argparse
import subprocess

import jinja2
import paramiko


def get_mlnx_ip_addr(hostname=None, username=None, password=None):
    """
        SSH to a host and get its IP
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Connect to remote host
        ssh.connect(hostname=hostname, username=username, password=password, timeout=15)
        _, stdout, _ = ssh.exec_command("/usr/sbin/ip -4 -o addr show dev bond0|awk '{print $4}'|cut -d '/' -f1")
        mlnx_ip = stdout.read().strip()

        # Validate it's an IP
        socket.inet_aton(mlnx_ip)

        # Close SSH connection
        ssh.close()
    except Exception:
        raise Exception('Failed to connect/get bond0 IP from {}'.format(hostname))
    return mlnx_ip


class Host(object):

    def __init__(self, mgmt_ip, user, password, has_etcd, is_master):
        self.mgmt_ip = mgmt_ip
        self.user = user
        self.password = password
        self.rdma_ip = get_mlnx_ip_addr(mgmt_ip, user, password)
        self.has_etcd = has_etcd
        self.is_master = is_master

    @classmethod
    def from_naipi_config(cls, path):
        with open(path) as fh:
            config = json.load(fh)

        return [cls._from_dict(client)
                for client in config['setup']['clients'] if 'kube-node' in client['roles']]

    @classmethod
    def _from_dict(cls, data):
        roles = data['roles']
        has_etcd = 'kube-etcd' in roles
        is_master = 'kube-master' in roles
        return cls(data['address'], data['username'], data['password'], has_etcd, is_master)


def _gen_templates(path, **kwargs):
    with open(path + '.jinja2') as fh:
        data = fh.read()

    template = jinja2.Template(
        data, keep_trailing_newline=True, trim_blocks=True,
        undefined=jinja2.StrictUndefined)
    generated_data = template.render(**kwargs)

    with open(path, 'w') as fh:
        fh.write(generated_data)


def invoke():
    subprocess.check_call(
        ['ansible-playbook', '-i', 'inventory/igz/hosts.ini', 'cluster.yml',
         '-u', 'iguazio', '-b', '--skip', '-tags=igz-online'])


def _parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('naipi_config')
    return parser.parse_args()


def main():
    log_fmt = '%(asctime)s %(levelname)s: %(filename)s:%(lineno)d: %(message)s'
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=log_fmt)

    args = _parse()

    hosts = Host.from_naipi_config(args.naipi_config)
    mgmt_ips = [host.mgmt_ip for host in hosts]

    logging.info('generating template files')
    templates = ['inventory/igz/hosts.ini', 'variables.yml']
    for template in templates:
        _gen_templates(template, hosts=hosts,
                       supplementary_addresses_in_ssl_keys=mgmt_ips)

    logging.info('start executing kubespray deploy')
    invoke()


if __name__ == '__main__':
    main()
