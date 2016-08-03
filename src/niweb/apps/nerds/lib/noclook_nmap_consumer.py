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

from datetime import datetime
import logging
import norduniclient as nc
import noclook_consumer as nt
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
    'skolfederation.se':'SUNET',
    'swami.se':         'SUNET',
    'swamid.se':        'SUNET',
    'uninett.no':       'UNINETT',
    'wayf.dk':          'WAYF',
}


def set_host_user(host):
    """
    Tries to set a Uses or Owns relationship between the Host and a Host User if there are none.
    """
    user = nt.get_user()
    domain = '.'.join(host.data['name'].split('.')[-2:])
    relations = host.get_relations()
    host_user_name = HOST_USERS_MAP.get(domain, None)
    if host_user_name and not (relations.get('Uses', None) or relations.get('Owns', None)):
        relation_node_handle = nt.get_unique_node_handle(host_user_name, 'Host User', 'Relation')
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


def set_not_public(host):
    """
    Set the hosts relationships to host services public property to false.

    :param host: neo4j node
    :return: None
    """
    q = '''
        MATCH (host {handle_id:{handle_id}})<-[r:Depends_on]-(host_service)
        WHERE has(r.public)
        SET r.public = false
        '''
    with nc.neo4jdb.transaction as t:
        t.execute(q, handle_id=host.handle_id).fetchall()


def insert_services(service_dict, host_node, external_check=False):
    """
    Takes a dictionary of services and a node id for a host. Gets or creates a
    service and makes a Depends_on relationship between the service and host.

    Example service_dict:
    {"127.0.0.1": {
        "tcp": {
            "80": {
                "conf": "10",
                "extrainfo": "",
                "name": "http",
                "product": "VMware ESXi Server httpd",
                "reason": "syn-ack",
                "state": "open",
                "version": ""
            },
            "8443": {
                "conf": "10",
                "extrainfo": "",
                "name": "ssl",
                "product": "TLS",
                "reason": "syn-ack",
                "state": "open",
                "version": "1.0"
            }
        }
    }
    """
    user = nt.get_user()
    node_type = "Host Service"
    meta_type = 'Logical'
    services_locked = host_node.data.get('services_locked', False)
    # Expected service data from nmap
    property_keys = ['ip_address', 'protocol', 'port', 'conf', 'extrainfo',
                     'name', 'product', 'reason', 'state', 'version']
    if external_check:
        property_keys.extend(['public', 'noclook_last_external_check'])
        external_dict = {
            'public': True,
            'noclook_last_external_check': datetime.now().isoformat()
        }
        set_not_public(host_node)
    for address in service_dict.keys():
        for protocol in service_dict[address].keys():
            for port in service_dict[address][protocol].keys():
                service = service_dict[address][protocol][port]
                if service['state'] != 'closed':
                    service_name = service['name']
                    if not service_name:  # Blank
                        service_name = 'unknown'
                    service_node_handle = nt.get_unique_node_handle(service_name, node_type, meta_type)
                    service_node = service_node_handle.get_node()
                    helpers.update_noclook_auto_manage(service_node)
                    relationship_properties = {
                        'ip_address': address,
                        'protocol': protocol,
                        'port': port
                    }
                    result = host_node.get_host_service(service_node.handle_id, **relationship_properties)
                    if not result.get('Depends_on'):
                        result = host_node.set_host_service(service_node.handle_id, **relationship_properties)
                    relationship_id = result.get('Depends_on')[0].get('relationship_id')
                    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
                    created = result.get('Depends_on')[0].get('created')
                    # Set or update relationship properties
                    relationship_properties.update(service)
                    if external_check:
                        relationship_properties.update(external_dict)
                    if created:
                        activitylog.create_relationship(user, relationship)
                        if services_locked:
                            logger.warn('New open port found for host {name}.'.format(name=host_node.data['name']))
                            property_keys.append('rogue_port')
                            relationship_properties['rogue_port'] = True
                        logger.info('Host Service {host_service_name} using port {port}/{protocol} created.'.format(
                            host_service_name=service_node.data['name'], port=relationship.data['port'],
                            protocol=relationship.data['protocol']
                        ))
                    if not created:
                        logger.info('Host Service {host_service_name} using port {port}/{protocol} found.'.format(
                            host_service_name=service_node.data['name'],
                            port=relationship.data['port'],
                            protocol=relationship.data['protocol']
                        ))
                    helpers.update_noclook_auto_manage(relationship)
                    helpers.dict_update_relationship(user, relationship.id, relationship_properties, property_keys)
                    logger.info('{name} {ip_address} {port}/{protocol} processed...'.format(
                        name=host_node.data['name'], ip_address=address, protocol=protocol, port=port))


def insert_nmap(json_list, external_check=False):
    """
    Inserts the data loaded from the json files created by
    the nerds producer nmap_services.
    """
    user = nt.get_user()
    node_type = "Host"
    meta_type = 'Logical'
    # Insert the host
    for i in json_list:
        name = i['host']['name']
        logger.info('%s loaded' % name)
        addresses = i['host']['nmap_services_py']['addresses']
        # Check if the ipaddresses matches any non-host node as a router interface for example
        if not is_host(addresses):
            logger.info('%s does not appear to be a host.' % name)
            continue
        # Get or create the NodeHandle and the Node by name, bail if there are more than one match
        node_handle = nt.get_unique_node_handle_by_name(name, node_type, meta_type, ALLOWED_NODE_TYPE_SET)
        if not node_handle or node_handle.node_type.type not in ALLOWED_NODE_TYPE_SET:
            continue
        # Set Node attributes
        node = node_handle.get_node()
        helpers.update_noclook_auto_manage(node)
        properties = {
            'hostnames': i['host']['nmap_services_py']['hostnames'],
            'ip_addresses': addresses
        }
        if 'os' in i['host']['nmap_services_py']:
            if 'class' in i['host']['nmap_services_py']['os']:
                properties['os'] = i['host']['nmap_services_py']['os']['class']['osfamily']
                properties['os_version'] = i['host']['nmap_services_py']['os']['class']['osgen']
            elif 'match' in i['host']['nmap_services_py']['os']:
                properties['os'] = i['host']['nmap_services_py']['os']['match']['name']
        if 'uptime' in i['host']['nmap_services_py']:
            properties['lastboot'] = i['host']['nmap_services_py']['uptime']['lastboot']
            properties['uptime'] = i['host']['nmap_services_py']['uptime']['seconds']
        insert_services(i['host']['nmap_services_py']['services'], node, external_check)
        # Check if the host has backup
        properties['backup'] = helpers.get_host_backup(node)
        # Set operational state if it is missing
        if not node.data.get('operational_state', None):
            properties['operational_state'] = 'In service'
        # Update host node
        helpers.dict_update_node(user, node.handle_id, properties, properties.keys())
        # Set host user depending on the domain.
        set_host_user(node)
        logger.info('%s done.' % name)


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?', help='Path to the configuration file.')
    parser.add_argument('-X', action='store_true', default=False, help='Mark host services as public if found.')
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    args = parser.parse_args()
    # Load the configuration file
    if not args.C:
        logger.error('Please provide a configuration file with -C.')
        sys.exit(1)
    else:
        if args.verbose:
            logger.setLevel(logging.INFO)
        config = nt.init_config(args.C)
        nmap_services_data = config.get('data', 'nmap_services_py')
        if nmap_services_data:
            insert_nmap(nt.load_json(nmap_services_data), args.X)
    return 0

if __name__ == '__main__':
    ## Need to change this path depending on where the Django project is
    ## located.
    import os
    import sys
    import argparse
    base_path = '../../../'
    sys.path.append(os.path.abspath(base_path))
    niweb_path = os.path.join(base_path, 'niweb')
    sys.path.append(os.path.abspath(niweb_path))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "niweb.settings.prod")

    logger.setLevel(logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    main()
