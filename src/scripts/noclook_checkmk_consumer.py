#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       noclook_checkmk_consumer.py
#
#       Copyright 2013 Johan Lundberg <lundberg@nordu.net>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import os
import sys
import argparse
from datetime import datetime, timedelta
from lucenequerybuilder import Q
from ipaddr import IPAddress

## Need to change this path depending on where the Django project is
## located.
#path = '/var/norduni/src/niweb/'
path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import norduni_client as nc
import noclook_consumer as nt
from apps.noclook import activitylog
from apps.noclook import helpers as h

# This script is used for adding the objects collected with the
# NERDS producer checkmk_livestatus.

VERBOSE = False

"""
{
    "host": {
        "checkmk_livestatus": {
            "checks": [
                {
                    "check_command": "check_ping!100.0,1%!500.0,2%",
                    "description": "PING",
                    "display_name": "PING",
                    "last_check": 1369703654,
                    "perf_data": "rta=0.494ms;100.000;500.000;0; pl=0%;1;2;; rtmax=0.574ms;;;; rtmin=0.452ms;;;;",
                    "plugin_output": "OK - 127.0.0.1: rta 0.494ms, lost 0%"
                },
                {
                    "check_command": "check_ssh",
                    "description": "SSH",
                    "display_name": "SSH",
                    "last_check": 1369703666,
                    "perf_data": "",
                    "plugin_output": "SSH OK - OpenSSH_5.9 NetBSD_Secure_Shell-20110907-hpn13v11-lpk (protocol 2.0)"
                },
                {
                    u'check_command': u'CHECK_NRPE!check_uptime',
                    u'description': u'check_uptime',
                    u'display_name': u'check_uptime',
                    u'last_check': 1370308217,
                    u'perf_data': u'type=1 uptime_minutes=25572'
                    u'plugin_output': u'OK: Linux ds1.sunet.se 2.6.32-47-generic-pae - up 17 days 18 hours 12 minutes',
                }
            ],
            "host_address": "127.0.0.1",
            "host_alias": "host.example.net",
            "host_name": "host"
        },
        "name": "ns1",
        "version": 1
    }
}
"""


def get_host(ip_address):
    """
    :param ip_address: string
    :return: neo4j node or None
    """
    index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
    q = Q('ip_addresses', '%s' % ip_address)
    for hit in index.query(unicode(q)):
        if hit['node_type'] == 'Host':  # Do we want to set nagios checks for other things?
            return hit


def set_nagios_checks(host, checks):
    """
    :param host: neo4j node
    :param checks: list of strings
    :return: None
    """
    checks = list(set(checks))
    checks.sort()
    property_dict = {
        'nagios_checks': checks
    }
    h.dict_update_node(nt.get_user(), host, property_dict, property_dict.keys())


def set_uptime(host, check):
    """
    Parses uptime collected with check_uptime (https://github.com/willixix/WL-NagiosPlugins).

    :param host: neo4j node
    :param check: check dictionary
    :return: None
    """
    try:
        last_check = datetime.utcfromtimestamp(check['last_check'])
        uptime = int(check['perf_data'].split('=')[-1]) * 60  # uptime in minutes to uptime in sec
        lastboot = last_check - timedelta(seconds=uptime)
        property_dict = {
            'lastboot': lastboot.strftime("%a %b %d %H:%M:%S %Y"),
            'uptime': uptime
        }
        h.dict_update_node(nt.get_user(), host, property_dict, property_dict.keys())
    except ValueError as e:
        if VERBOSE:
            print '%s uptime check did not match the expected format.' % host['name']
            print check
            print e


def insert(json_list):
    for item in json_list:
        base = item['host']['checkmk_livestatus']
        ip_address = base['host_address']
        host = get_host(ip_address)
        if host:
            check_descriptions = []
            for check in base['checks']:
                check_descriptions.append(check.get('description', 'Missing description'))
                if check['check_command'] == 'CHECK_NRPE!check_uptime':  # Host uptime
                    set_uptime(host, check)
            set_nagios_checks(host, check_descriptions)
            h.update_noclook_auto_manage(nc.neo4jdb, host)
            if VERBOSE:
                print '%s done.' % host['name']


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?', help='Path to the configuration file.')
    parser.add_argument('--verbose', '-v', default=False, action='store_true',
                        help='Verbose output')
    args = parser.parse_args()
    if args.verbose:
        global VERBOSE
        VERBOSE = True
    # Load the configuration file
    if not args.C:
        print 'Please provide a configuration file with -C.'
        sys.exit(1)
    else:
        config = nt.init_config(args.C)
        nagios_checkmk_data = config.get('data', 'nagios_checkmk')
        if nagios_checkmk_data:
            insert(nt.load_json(nagios_checkmk_data))
    return 0

if __name__ == '__main__':
    main()
