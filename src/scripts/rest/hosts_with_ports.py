#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'lundberg'

import sys
import os
import argparse
from collections import defaultdict
from apiclient import NIApiClient

USER = os.environ.get('USER', '')
APIKEY = os.environ.get('API_KEY', '')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost')
VERBOSE = False


def get_host_scan(output_file):
    client = NIApiClient(BASE_URL, USER, APIKEY)
    for host in client.get_host_scan():
        tcp_ports, udp_ports = '', ''
        if host.get('tcp_ports', None):
            tcp_ports = 'T:{},'.format(','.join(host['tcp_ports']))
        if host.get('udp_ports', None):
            udp_ports = 'U:{}'.format(','.join(host['udp_ports']))
        if tcp_ports or udp_ports:
            for ip_address in host.get('ip_addresses', []):
                output_file.writelines('{ip} {tcp}{udp}\n'.format(ip=ip_address, tcp=tcp_ports, udp=udp_ports))


# Deprecated old version that traverses hostsm nd gets dependencies. Use get_host_scan.
def get_hosts(output_file):
    client = NIApiClient(BASE_URL, USER, APIKEY)
    for host in client.get_type('host', headers=client.create_headers()):
        if host['node'].get('operational_state', 'Not set') != 'Decommissioned':
            if VERBOSE:
                print('Getting ports for %s...' % host['node_name']),
            ports = defaultdict(list)
            for rel in client.get_relationships(host, relationship_type='Depends_on', headers=client.create_headers()):
                protocol = rel['properties'].get('protocol', None)
                port = rel['properties'].get('port', None)
                if protocol and port:
                    ports[protocol].append(port)
            tcp_ports, udp_ports = '', ''
            if 'tcp' in ports:
                tcp_ports = 'T:%s,' % ','.join([str(i) for i in set(ports['tcp'])])
            if 'udp' in ports:
                udp_ports = 'U:%s' % ','.join([str(i) for i in set(ports['udp'])])
            if tcp_ports or udp_ports:
                for ip_address in host['node'].get('ip_addresses', []):
                    output_file.writelines('%s %s%s\n' % (ip_address, tcp_ports, udp_ports))
            if VERBOSE:
                print('done.')


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', '-O', default=sys.stdout, type=argparse.FileType('wb', 0))
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    args = parser.parse_args()
    if args.verbose:
        global VERBOSE
        VERBOSE = True
    get_host_scan(args.output)
    args.output.close()
    return 0

if __name__ == '__main__':
    main()
