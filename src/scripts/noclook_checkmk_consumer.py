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
import re
import logging

## Need to change this path depending on where the Django project is
## located.
base_path = '../niweb/'
sys.path.append(os.path.abspath(base_path))
niweb_path = os.path.join(base_path, 'niweb')
sys.path.append(os.path.abspath(niweb_path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.conf import settings as django_settings
import norduniclient as nc
import noclook_consumer as nt
from apps.noclook import helpers

logger = logging.getLogger('noclook_consumer.checkmk')

# This script is used for adding the objects collected with the
# NERDS producer checkmk_livestatus.

"""
{
    "host": {
        "checkmk_livestatus": {
            "checks": [
                {
                    "check_command": "check_netapp_vol!cifs_id5!90!95",
                    "description": "NetApp vol4 storage volume",
                    "display_name": "NetApp vol4 storage volume",
                    "last_check": 1389748268,
                    "perf_data": "",
                    "plugin_output": "OK - cifs_id5 usage: 573.54 / 1003.52 GB (57.15%) 92586/31876689 files (0.29%)"
                },
                {
                    "check_command": "CHECK_NRPE!check_backup",
                    "description": "check backup",
                    "display_name": "check backup",
                    "last_check": 1389748307,
                    "perf_data": "",
                    "plugin_output": "PROCS OK: 1 process with UID = 0 (root), args 'dsmcad'"
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
    q = Q('ip_addresses', '%s' % ip_address)
    search = nc.legacy_node_index_search(nc.neo4jdb, unicode(q))
    for handle_id in search['result']:
        node = nc.get_node_model(nc.neo4jdb, handle_id)
        if 'Host' in node.labels:
            return node


def set_nagios_checks(host, checks):
    """
    :param host: norduniclient node model
    :param checks: list of strings
    :return: None
    """
    checks = list(set(checks))
    checks.sort()
    property_dict = {
        'nagios_checks': checks
    }
    helpers.dict_update_node(nt.get_user(), host.handle_id, property_dict, property_dict.keys())


def set_uptime(host, check):
    """
    Parses uptime collected with check_uptime (https://github.com/willixix/WL-NagiosPlugins).

    :param host: norduniclient node model
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
        helpers.dict_update_node(nt.get_user(), host.handle_id, property_dict, property_dict.keys())
    except ValueError as e:
        logger.info('{name} uptime check did not match the expected format.'.format(name=host.data['name']))
        logger.info(check)
        logger.info(e)


def set_backup(host, check):
    """
    Parses output from check_backup, looks for known backup processes and if the check returned ok.

    :param host: norduniclient node model
    :param check: check dictionary
    :return: None
    """
    try:
        if 'PROCS OK' in check['plugin_output'] and 'dsmcad' in check['plugin_output']:
            property_dict = {
                'backup': 'tsm'
            }
            helpers.dict_update_node(nt.get_user(), host.handle_id, property_dict, property_dict.keys())
    except ValueError as e:
        logger.info('{name} backup check did not match the expected format.'.format(name=host.data['name']))
        logger.info(check)
        logger.info(e)


def collect_netapp_storage_usage(host, check, storage_collection):
    """
    :param host: norduniclient node model
    :param check: check dictionary
    :param storage_collection: persistent list for collecting data
    :return: list storage_collection
    """
    plugin_output = check['plugin_output']
    for service in storage_collection:
        for pattern in service['volumes']:
            if pattern.search(plugin_output):
                try:
                    service['total_storage'] += float(plugin_output.split('usage:')[1].split()[0])
                except ValueError as e:
                    logger.error('{name} Netapp storage check did not match the expected format.'.format(
                        name=host.data['name']))
                    logger.error(check)
                    logger.error(e)
    return storage_collection


def set_netapp_storage_usage(storage_collection):
    """
    :param storage_collection: list
    :return: None
    """
    for service in storage_collection:
        service_node = nc.get_unique_node_by_name(nc.neo4jdb, service['service_id'], 'Service')
        property_dict = {'netapp_storage_sum': service['total_storage']}
        helpers.dict_update_node(nt.get_user(), service_node.handle_id, property_dict, property_dict.keys())
        service['total_storage'] = 0.0


def set_dell_service_tag(host, check):
    """
    :param host: norduniclient node model
    :param check: check dictionary
    :return: None
    """
    tag = None
    try:
        openmanage_linux_tag_regex = re.compile('servicetag=(?P<tag>[\w]+)', re.IGNORECASE)
        tag = openmanage_linux_tag_regex.search(check['plugin_output']).group('tag')
    except AttributeError:
        pass
    try:
        openmanage_win_tag_regex = re.compile('SN: \'(?P<tag>[\w]+)\'', re.IGNORECASE)
        tag = openmanage_win_tag_regex.search(check['plugin_output']).group('tag')
    except AttributeError:
        pass
    try:
        esxi_tag_regex = re.compile('s/n: (?P<tag>[\w]+)', re.IGNORECASE)
        tag = esxi_tag_regex.search(check['plugin_output']).group('tag')
    except AttributeError:
        pass
    if tag:
        property_dict = {'service_tag': tag}
        helpers.dict_update_node(nt.get_user(), host.handle_id, property_dict, property_dict.keys())


def insert(json_list):

    # Setup persistent storage for collections done over multiple hosts
    netapp_collection = getattr(django_settings, 'NETAPP_REPORT_SETTINGS', [])

    # Parse collected Nagios data
    for item in json_list:
        base = item['host']['checkmk_livestatus']
        host = nc.get_unique_node_by_name(nc.neo4jdb, base['host_name'], 'Host')
        if not host:
            host = get_host(base['host_address'])
        if host:
            check_descriptions = []
            for check in base['checks']:
                check_descriptions.append(check.get('description', 'Missing description'))
                if check['check_command'] == 'CHECK_NRPE!check_uptime':     # Host uptime
                    set_uptime(host, check)
                if check['check_command'] == 'CHECK_NRPE!check_backup':     # TSM backup process
                    set_backup(host, check)
                if check['check_command'].startswith('check_netapp_vol'):   # NetApp storage usage
                    netapp_collection = collect_netapp_storage_usage(host, check, netapp_collection)
                if check['check_command'] == 'CHECK_NRPE!check_openmanage':     # Dell OpenManage info
                    set_dell_service_tag(host, check)
                if check['check_command'] == 'check_esxi':                      # Dell esxi HW info
                    set_dell_service_tag(host, check)
            set_nagios_checks(host, check_descriptions)
            helpers.update_noclook_auto_manage(host)
            logger.info('{name} done.'.format(name=host.data['name']))
    # Set data collected from multiple hosts
    set_netapp_storage_usage(netapp_collection)


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?', help='Path to the configuration file.')
    parser.add_argument('--verbose', '-V', default=False, action='store_true',
                        help='Verbose output')
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.INFO)
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
    logger.setLevel(logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    main()
