#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       noclook_consumer.py
#
#       Copyright 2010 Johan Lundberg <lundberg@nordu.net>
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

import sys
import argparse
from datetime import datetime
import logging
import utils

import norduniclient as nc
from apps.noclook import activitylog
from apps.noclook import helpers
from apps.nerds.lib.consumer_util import address_is_a

logger = logging.getLogger('noclook_consumer.nmap')


# This script is used for adding the objects collected with the
# NERDS producers to the NOCLook database viewer.

# Type of equipment we want to update with this consumer
ALLOWED_NODE_TYPE_SET = {'Host', 'Firewall', 'Switch', 'PDU'}

HOST_USERS_MAP = {
    'eduroam.se':       'SUNET',
    'eduid.se':         'SUNET',
    'eid2.se':          'SUNET',
    'funet.fi':         'FUNET',
    'lobber.se':        'SUNET',
    'ndgf.org':         'NDGF',
    'nordu.net':        'NORDUnet',
    'nordunet.tv':      'NORDUnet',
    'nunoc.org':        'NORDUnet',
    'nunoc.se':         'NORDUnet',
    'sunet.se':         'SUNET',
    'rhnet.is':         'RHnet',
    'skolfederation.se': 'SUNET',
    'swami.se':         'SUNET',
    'swamid.se':        'SUNET',
    'uninett.no':       'UNINETT',
    'wayf.dk':          'WAYF',
}


def set_host_user(host):
    """
    Tries to set a Uses or Owns relationship between the Host and a Host User if there are none.
    """
    user = utils.get_user()
    domain = '.'.join(host.data['name'].split('.')[-2:])
    relations = host.get_relations()
    host_user_name = HOST_USERS_MAP.get(domain, None)
    if host_user_name and not (relations.get('Uses', None) or relations.get('Owns', None)):
        relation_node_handle = utils.get_unique_node_handle(
            host_user_name, 'Host User', 'Relation')
        if host.meta_type == 'Logical':
            helpers.set_user(user, host, relation_node_handle.handle_id)
        elif host.meta_type == 'Physical':
            helpers.set_owner(user, host, relation_node_handle.handle_id)
        logger.info('Host User {user_name} set for host {host_name}.'.format(user_name=host_user_name,
                                                                             host_name=host.data['name']))


def is_host(addresses):
    """
    :param addresses: List of IP addresses
    :return: True if the addresses belongs to a host or does not belong to anything
    """
    return address_is_a(addresses, ALLOWED_NODE_TYPE_SET)


def insert_nmap(json_list, external_check=False):
    """
    Inserts the data loaded from the json files created by
    the nerds producer nmap_services.
    """
    user = utils.get_user()
    node_type = "Host"
    meta_type = 'Logical'
    # Insert the host
    for i in json_list:
        name = i['host']['name'].lower()
        i['host']['name'] = name
        logger.info('%s loaded' % name)
        addresses = i['host']['nmap_services_py']['addresses']
        # Check if the ipaddresses matches any non-host node as a router interface for example
        if not is_host(addresses):
            logger.info('%s does not appear to be a host.' % name)
            continue
        # Get or create the NodeHandle and the Node by name, bail if there are more than one match
        node_handle = utils.get_unique_node_handle_by_name(
            name, node_type, meta_type, ALLOWED_NODE_TYPE_SET)
        if not node_handle or node_handle.node_type.type not in ALLOWED_NODE_TYPE_SET:
            continue
        # Set Node attributes
        node = node_handle.get_node()
        helpers.update_noclook_auto_manage(node)

        # dont replace if addesses are already in current addresses
        if set(addresses).issubset(set(node.data.get('ip_addresses', []))):
            addresses = []

        properties = {
            'hostnames': i['host']['nmap_services_py']['hostnames'],
            'ip_addresses': addresses
        }

        # disable insert_services import, last_seen is updated by update_noclook_auto_manage.
        # insert_services(i['host']['nmap_services_py']['services'], node, external_check)

        # Check if the host has backup
        properties['backup'] = helpers.get_host_backup(node)
        # Set operational state if it is missing
        if not node.data.get('operational_state', None):
            properties['operational_state'] = 'In service'
        # Update host node
        helpers.dict_update_node(user, node.handle_id,
                                 properties, properties.keys())
        # Set host user depending on the domain.
        set_host_user(node)
        logger.info('%s done.' % name)


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-C', nargs='?', help='Path to the configuration file.')
    parser.add_argument('-X', action='store_true', default=False,
                        help='Mark host services as public if found.')
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    args = parser.parse_args()
    # Load the configuration file
    if not args.C:
        logger.error('Please provide a configuration file with -C.')
        sys.exit(1)
    else:
        if args.verbose:
            logger.setLevel(logging.INFO)
        config = utils.init_config(args.C)
        nmap_services_data = config.get('data', 'nmap_services_py')
        if nmap_services_data:
            insert_nmap(utils.load_json(nmap_services_data), args.X)
    return 0


if __name__ == '__main__':
    logger.setLevel(logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    main()
