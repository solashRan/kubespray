#!/usr/bin/env python
import sys
import json
import socket
import logging
import os.path
import argparse
import contextlib

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


class ClientNode(object):

    def __init__(self, mgmt_ip, user, password):
        self.mgmt_ip = mgmt_ip
        self.user = user
        self.password = password

    @classmethod
    def from_json(cls, data):
        data = json.loads(data)
        return cls(data['mgmt_ip'], data['user'], data['password'])

    def put_file(self, local_path, dest_path):
        dest_dir = os.path.dirname(dest_path)
        with self._sftp() as sftp:
            try:
                sftp.mkdir(dest_dir, 0o755)
            except IOError:
                # if folder exists its ok
                pass

            sftp.put(local_path, dest_path)

    @contextlib.contextmanager
    def _sftp(self):
        transport = paramiko.Transport((self.mgmt_ip, 22))
        transport.connect(username=self.user, password=self.password)
        try:
            sftp = paramiko.SFTPClient.from_transport(transport)
            try:
                yield sftp
            finally:
                sftp.close()
        finally:
            transport.close()


class ServerHost(object):

    def __init__(self, mgmt_ip, user, password, rdma_ip, has_etcd, is_master):
        self.mgmt_ip = mgmt_ip
        self.user = user
        self.password = password
        self.rdma_ip = rdma_ip or get_mlnx_ip_addr(mgmt_ip, user, password)
        self.has_etcd = has_etcd
        self.is_master = is_master

    @classmethod
    def from_json(cls, data):
        data = json.loads(data)
        return cls(data['mgmt_ip'], data['user'], data['password'], data.get('rdma_ip'),
                   data['has_etcd'], data['is_master'])


def _gen_templates(path, **kwargs):
    with open(path + '.jinja2') as fh:
        data = fh.read()

    template = jinja2.Template(
        data, keep_trailing_newline=True, trim_blocks=True,
        undefined=jinja2.StrictUndefined)
    generated_data = template.render(**kwargs)

    with open(path, 'w') as fh:
        fh.write(generated_data)


# def copy_admin_conf_to_data_nodes(naipi_config):
#     data_nodes = DataNode.from_naipi_config(naipi_config)
#     for data_node in data_nodes:
#         data_node.put_file('inventory/igz/artifacts/admin.conf', '/home/iguazio/.kube/admin.conf')


def _parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server', dest='servers', action='append', type=ServerHost.from_json, default=[])
    parser.add_argument('-c', '--client', dest='clients', action='append', type=ClientNode.from_json, default=[])
    return parser.parse_args()


def main():
    log_fmt = '%(asctime)s %(levelname)s: %(filename)s:%(lineno)d: %(message)s'
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=log_fmt)

    args = _parse()

    logging.info('generating template files')
    templates = ['inventory/igz/hosts.ini', 'variables.yml']
    for template in templates:
        _gen_templates(template, servers=args.servers, clients=args.clients)


if __name__ == '__main__':
    main()
