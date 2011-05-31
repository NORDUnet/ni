#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       noclook_juniper_consumer.py
#
#       Copyright 2011 Johan Lundberg <lundberg@nordu.net>
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
import json
import argparse
import ipaddr

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

'''
This script is used for adding the objects collected with the
NERDS producers juniper_config to the NOCLook database viewer.

JSON format used:
{["host": {
    "juniper_conf": {
        "bgp_peerings": [
            {    
            "as_number": "", 
            "group": "", 
            "description": "", 
            "remote_address": "", 
            "local_address": "", 
            "type": ""
            },
        ], 
        "interfaces": [
            {
            "name": "", 
            "bundle": "", 
            "vlantagging": true/false, 
            "units": [
                {
                "address": [
                "", 
                ""
                ], 
                "description": "", 
                "unit": "", 
                "vlanid": ""
                }
            ], 
            "tunnels": [
            {
            "source": "", 
            "destination": ""
            }
            ], 
            "description": ""
            }, 
        ],
        "name": ""
        }, 
        "version": 1, 
        "name": ""        
    }
]}
'''

def insert_juniper_router(name):
    '''
    Inserts a physical meta type node of the type Router.
    Returns the node created.
    '''
    node_handle = nt.get_unique_node_handle(name, 'Router', 'physical')
    node = node_handle.get_node()
    node_list = [node]
    return node_list

def insert_juniper_interfaces(router_node, interfaces):
    '''
    Insert all interfaces in the interfaces list with a Has
    relationship from the router_node. Some filtering is done for
    interface names that are not interesting.
    Returns a list with all created nodes.
    '''
    not_interesting_interfaces = ['all', 'fxp0', '']
    node_list = []
    for i in interfaces:
        name = i['name']
        if name not in not_interesting_interfaces:
            # Also "not interesting" is interfaces with . or * in their
            # names
            if '.' not in name and '*' not in name:
                node_handle = nt.get_node_handle(name, 'PIC', 'physical', 
                                                                    router_node)
                node = nc.get_node_by_id(node_handle.node_id)
                node['description'] = nt.rest_comp(i['description'])
                node['units'] = json.dumps(i['units'])
                if not nc.get_relationships(router_node, node, 'Has'):
                    # Only create a relationship if it doesn't exist
                    router_node.Has(node)
                node_list.append(node)

    return node_list

def insert_juniper_relation(name, as_number):
    '''
    Inserts a relation meta type node of the type Peering partner.
    Returns the newly created node.
    '''
    node_handle = nt.get_unique_node_handle(name, 'Peering Partner', 'relation')
    node = nc.get_node_by_id(node_handle.node_id)
    node['as_number'] = nt.rest_comp(as_number)
    node_list = [node]

    return node_list

def insert_juniper_service(name):
    '''
    Inserts a logical meta type node of the type IP Service.
    Returns the newly created node.
    '''
    node_handle = nt.get_unique_node_handle(name, 'IP Service', 'logical')
    node = nc.get_node_by_id(node_handle.node_id)
    node_list = [node]

    return node_list

def insert_juniper_bgp_peerings(bgp_peerings):
    '''
    Inserts all BGP peerings for all routers collected by the
    juniper_conf producer. This is to be able to get all the internal
    peerings associated to the right interfaces.
    Returns a list of all created peering nodes.
    '''
    for p in bgp_peerings:
        name = p['description']
        if name == None:
            name = 'No description'
        group = p['group']
        service = nc.get_node_by_value(group, 'logical', 'name')
        if not service:
            service = insert_juniper_service(group)
        peering_type = p['type']
        if peering_type == 'internal':
            remote_addr = ipaddr.IPAddress(p['remote_address'])
            local_addr = ipaddr.IPAddress(p['local_address'])
        elif peering_type == 'external':
            peeringp = nc.get_node_by_value(p['as_number'], 'relation', 'as_number')
            if not peeringp:
                peeringp = insert_juniper_relation(name, p['as_number'])
            rel_uses = nc.get_relationships(peeringp[0], service[0], 'Uses')
            create = True
            for rel in rel_uses:
                if rel['ip_address'] == p['remote_address']:
                    # Already have this relationship
                    create = False
            if create:
                # Only create a relationship if it doesn't exist
                peeringp[0].Uses(service[0], ip_address=p['remote_address'])
            remote_addr = ipaddr.IPAddress(p['remote_address'])
            local_addr = ipaddr.IPAddress('0.0.0.0') #None did not work
        # Loop through interfaces to find the local and/or remote
        # address
        for pic in nc.get_node_by_value('PIC', 'physical', 'node_type'):            
            units = json.loads(pic['units'])
            # Gah, this next part needs to be refactored, it is hard
            # to read and ugly...
            for unit in units:     
                for addr in unit['address']:
                    try:
                        pic_addr = ipaddr.IPNetwork(addr)
                    except ValueError:
                        # ISO address on lo0
                        break
                    if local_addr in pic_addr or \
                                            remote_addr in pic_addr:
                        rels = nc.get_relationships(service[0],
                                            pic, 'Depends_on')
                        create = True # Create new relation
                        for rel in rels:
                            # Can't have more than one unit with the
                            # same unit number
                            if rel['unit'] == unit['unit']:
                                create = False  # Do not create a
                                break           # new relation
                        if create:
                            service[0].Depends_on(pic,
                                    ip_address=addr,
                                    unit=unit['unit'],
                                    vlan=unit['vlanid'],
                                    description=unit['description'])
                            break

def consume_juniper_conf(json_list):
    '''
    Inserts the data loaded from the json files created by the nerds
    producer juniper_conf.
    Some filtering is done for interface names that are not interesting.
    '''
    bgp_peerings = []
    for i in json_list:
        name = i['host']['juniper_conf']['name']
        router_node = insert_juniper_router(name)[0]
        interfaces = i['host']['juniper_conf']['interfaces']
        insert_juniper_interfaces(router_node,
                            interfaces)
        bgp_peerings += i['host']['juniper_conf']['bgp_peerings']
    insert_juniper_bgp_peerings(bgp_peerings)

def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?',
        help='Path to the configuration file.')
    parser.add_argument('-I', action='store_true',
        help='Insert data in to the database.')
    args = parser.parse_args()
    # Load the configuration file
    if not args.C:
        print 'Please provide a configuration file with -C.'
        sys.exit(1)
    else:
        config = nt.init_config(args.C)
    # Insert data from known data sources if option -I was used
    if args.I:
        if config.get('data', 'juniper_conf'):
            consume_juniper_conf(nt.load_json(
                                    config.get('data', 'juniper_conf')))
    return 0

if __name__ == '__main__':
    main()
