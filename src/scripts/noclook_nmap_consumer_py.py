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

import os
import sys
import argparse
from lucenequerybuilder import Q

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
# NERDS producers to the NOCLook database viewer.

VERBOSE = True

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

def set_host_user(node):
    """
    Tries to set a Uses or Owns relationship between the Host and a Host User if there are none.
    """
    user = nt.get_user()
    q = '''
        START node=node({id})
        MATCH node<-[r:Owns|Uses]-()
        return COUNT(r) as rels
        '''
    hits = nc.neo4jdb.query(q, id=node.getId())
    users = int(str(h.iter2list(hits['rels'])[0])) # Hack...hits['rels'] is of type java.lang.Long...
    domain = '.'.join(node['name'].split('.')[-2:])
    host_user_name = HOST_USERS_MAP.get(domain, None)
    if host_user_name and not users:
        node_handle = nt.get_unique_node_handle(nc.neo4jdb, host_user_name,
                                                'Host User', 'relation')
        host_user = node_handle.get_node()
        if nc.get_node_meta_type(node) == 'logical':
            rel = nc.create_relationship(nc.neo4jdb, host_user, node, 'Uses')
            activitylog.create_relationship(user, rel)
        elif nc.get_node_meta_type(node) == 'physical':
            rel = nc.create_relationship(nc.neo4jdb, host_user, node, 'Owns')
            activitylog.create_relationship(user, rel)
        h.update_node_search_index(nc.neo4jdb, host_user)
        if VERBOSE:
            print 'User %s set for host %s...' % (host_user_name, node['name'])

def insert_services(service_dict, host_node):
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
    meta_type = 'logical'
    service_nodes = []
    # Expected service data from nmap
    property_keys = ['ip_address', 'protocol', 'port' 'conf', 'extrainfo',
                     'name', 'product', 'reason', 'state', 'version']
    for key in service_dict.keys():
        address = key
        for key in service_dict[address].keys():
            protocol = key
            for key in service_dict[address][protocol].keys():
                port = key
                service = service_dict[address][protocol][port]
                node_handle = nt.get_unique_node_handle(
                    nc.neo4jdb,
                    service['name'],
                    node_type,
                    meta_type
                )
                service_node = node_handle.get_node()
                h.update_noclook_auto_manage(nc.neo4jdb, service_node)
                service_nodes.append(service_node)
                # Get existing relationships between the two nodes
                rel_index = nc.get_relationship_index(nc.neo4jdb, nc.search_index_name())
                q = Q('ip_address', '%s' % address)
                service_rels = rel_index.query(str(q))
                create = True
                rel_dict = {
                    'ip_address': address,
                    'protocol': protocol,
                    'port': port
                }
                for key, value in service.items():
                    rel_dict[key] = value
                # Try to find an already existing relationship
                for rel in service_rels:
                    try:
                        if rel['protocol'] == protocol and rel['port'] == port:
                            create = False
                            h.dict_update_relationship(user, rel, rel_dict, property_keys)
                            h.update_noclook_auto_manage(nc.neo4jdb, rel)
                            break
                    except KeyError:
                        continue
                # Relationship did not exist
                if create:
                    # Create a relationship between the service and host
                    new_rel = nc.create_relationship(nc.neo4jdb, service_node, host_node,
                                                     'Depends_on')
                    h.dict_update_relationship(user, new_rel, rel_dict, property_keys)
                    h.update_noclook_auto_manage(nc.neo4jdb, new_rel)
                    h.update_relationship_search_index(nc.neo4jdb, new_rel)
                    activitylog.create_relationship(user, new_rel)
                if VERBOSE:
                    print '%s %s %s %s processed...' % (host_node['name'], address, protocol, port)
    return service_nodes

def insert_nmap(json_list):
    """
    Inserts the data loaded from the json files created by
    the nerds producer nmap_services.
    """
    user = nt.get_user()
    node_type = "Host"
    meta_type = 'logical'
    # Insert the host
    for i in json_list:
        name = i['host']['name']
        # Create the NodeHandle and the Node
        node_handle = nt.get_unique_node_handle(nc.neo4jdb, name, node_type,
                                                meta_type)
        # Set Node attributes
        property_keys = ['hostnames', 'addresses']
        node = node_handle.get_node()
        h.update_noclook_auto_manage(nc.neo4jdb, node)
        host_properties = {
            'hostnames': i['host']['nmap_services_py']['hostnames'],
            'addresses': i['host']['nmap_services_py']['addresses']
        }
        if 'os' in i['host']['nmap_services_py'] and not node.get_property('os', None):
            # Only set os if the property is missing as a user probably knows better than nmap
            if 'class' in i['host']['nmap_services_py']['os']:
                property_keys.extend(['os', 'os_version'])
                host_properties['os'] = i['host']['nmap_services_py']['os']['class']['osfamily']
                host_properties['os_version'] = i['host']['nmap_services_py']['os']['class']['osgen']
            elif 'match' in i['host']['nmap_services_py']['os']:
                property_keys.extend(['os'])
                host_properties['os'] = i['host']['nmap_services_py']['os']['match']['name']
        if 'uptime' in i['host']['nmap_services_py']:
            property_keys.extend(['lastboot', 'uptime'])
            host_properties['lastboot'] = i['host']['nmap_services_py']['uptime']['lastboot']
            host_properties['uptime'] = i['host']['nmap_services_py']['uptime']['seconds']
        h.dict_update_node(user, node, host_properties, property_keys)
        try:
            insert_services(i['host']['nmap_services_py']['services'], node)
        except KeyError as e:
            pass
        # Set host user depending on the domain.
        set_host_user(node)
        if VERBOSE:
            print '%s done.' % name

def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?',
        help='Path to the configuration file.')
    args = parser.parse_args()
    # Load the configuration file
    if not args.C:
        print 'Please provide a configuration file with -C.'
        sys.exit(1)
    else:
        config = nt.init_config(args.C)
        nmap_services_data = config.get('data', 'nmap_services_py')
        if nmap_services_data:
            insert_nmap(nt.load_json(nmap_services_data))
    return 0

if __name__ == '__main__':
    main()
