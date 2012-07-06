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
import re
import argparse
import ipaddr
from lucenequerybuilder import Q

## Need to change this path depending on where the Django project is
## located.
#path = '/var/norduni/src/niweb/'
path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import noclook_consumer as nt
from apps.noclook import helpers as h
import norduni_client as nc

# This script is used for adding the objects collected with the
# NERDS producers juniper_config to the NOCLook database viewer.
#
# JSON format used:
#{["host": {
#   "juniper_conf": {
#       "bgp_peerings": [
#            {
#            "as_number": "",
#            "group": "",
#            "description": "",
#            "remote_address": "",
#            "local_address": "",
#            "type": ""
#            },
#        ],
#        "interfaces": [
#            {
#            "name": "",
#            "bundle": "",
#            "vlantagging": true/false,
#            "units": [
#                {
#                "address": [
#                "",
#                ""
#                ],
#                "description": "",
#                "unit": "",
#                "vlanid": ""
#                }
#            ],
#            "tunnels": [
#            {
#            "source": "",
#            "destination": ""
#            }
#            ],
#            "description": ""
#            },
#        ],
#        "name": ""
#        },
#        "version": 1,
#        "name": ""
#    }
#]}

def insert_juniper_router(name):
    """
    Inserts a physical meta type node of the type Router.
    Returns the node created.
    """
    node_handle = nt.get_unique_node_handle(nc.neo4jdb, name, 'Router', 
                                            'physical')
    node = node_handle.get_node()
    h.set_noclook_auto_manage(nc.neo4jdb, node, True)
    h.update_node_search_index(nc.neo4jdb, node)
    return node

def insert_interface_unit(interf_node, unit):
    """
    Creates or updates logical interface units.
    """
    # Unit numbers are unique per interface
    create = True
    for rel in interf_node.Depends_on.incoming:
        if int(rel.start['name']) == int(unit['unit']):
            create = False
            node = rel.start
            break
    if create:
        node_handle = nt.get_node_handle(nc.neo4jdb, unit['unit'], 'Unit',
                                         'logical', interf_node)
        node = node_handle.get_node()
    h.set_noclook_auto_manage(nc.neo4jdb, node, True)
    with nc.neo4jdb.transaction:
        if unit['description']:
            node['description'] = unit['description']
        else:
            node['description'] = 'No description'
        if unit['address']:
            node['ip_addresses'] = unit['address']
        if unit['vlanid']:
            node['vlanid'] = unit['vlanid']
    rels = nc.get_relationships(node, interf_node, 'Depends_on')
    if rels:
        for rel in rels:
            h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
    else:
        # Only create a relationship if it doesn't exist
        rel = nc.create_relationship(nc.neo4jdb, node, interf_node,
                                        'Depends_on')
        h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
    # Add the node description and IP addresses to search index
    h.update_node_search_index(nc.neo4jdb, node)

def insert_juniper_interfaces(router_node, interfaces):
    """
    Insert all interfaces in the interfaces list with a Has
    relationship from the router_node. Some filtering is done for
    interface names that are not interesting.
    Returns a list with all created nodes.
    """
    not_interesting_interfaces = re.compile(r'.*\*|\.|all|fxp0.*')
    for i in interfaces:
        name = i['name']
        if name and not not_interesting_interfaces.match(name):
            node_handle = nt.get_node_handle(nc.neo4jdb, name, 'PIC', 
                                             'physical', router_node)
            node = node_handle.get_node()
            h.set_noclook_auto_manage(nc.neo4jdb, node, True)
            with nc.neo4jdb.transaction:
                if i['description']:
                    node['description'] = i['description']
                else:
                    node['description'] = 'No description'
                for unit in i['units']:
                    insert_interface_unit(node, unit)
                rels = nc.get_relationships(router_node, node, 'Has')
                if rels:
                    for rel in rels:
                        h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
                    # Only create a relationship if it doesn't exist
                else:
                    rel =  nc.create_relationship(nc.neo4jdb,
                                                           router_node, node, 
                                                           'Has')
                    h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
            # Add the node description and IP addresses to search index
            h.update_node_search_index(nc.neo4jdb, node)

def get_peering_partner(peering):
    """
    Inserts a new node of the type Peering partner and ensures that this node
    is unique for AS number.
    Returns the created node.
    """
    name = peering.get('description', None)
    if not name:
        name = 'Missing description'
    as_number = peering.get('as_number', None)
    if not as_number:
        as_number = '0'
    index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
    try:
        node = h.iter2list(index['as_number'][as_number])[0]
        h.set_noclook_auto_manage(nc.neo4jdb, node, True)
        if node['name'] != name and name != 'Missing description':
            with nc.neo4jdb.transaction:        
                node['name'] = name
        h.update_node_search_index(nc.neo4jdb, node)
    except IndexError:
        node_handle = nt.get_node_handle(nc.neo4jdb, name, 'Peering Partner',
                                         'relation')
        node = node_handle.get_node()
        h.set_noclook_auto_manage(nc.neo4jdb, node, True)
        with nc.neo4jdb.transaction:
            node['as_number'] = as_number
            # Add the nodes as_number to search index        
            h.update_node_search_index(nc.neo4jdb, node)
    return node

def match_remote_ip_address(remote_address):
    """
    Matches a remote address to a local interface.
    Returns a Unit node if match found or else None.
    """
    node_index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
    for prefix in [3, 2, 1]:
        if remote_address.version == 4:
            mask = '.'.join(str(remote_address).split('.')[0:prefix])
        elif remote_address.version == 6:
            mask = ':'.join(remote_address.exploded.split(':')[0:prefix])
        q = Q('ip_addresses', '%s*' % mask, wildcard=True)
        hits = node_index.query(str(q))
        for hit in hits:
            for addr in hit['ip_addresses']:
                try:
                    local_network = ipaddr.IPNetwork(addr)
                except ValueError:
                    continue # ISO address
                if remote_address in local_network:
                    return hit, addr
    return None, None

def insert_internal_bgp_peering(peering, service_node):
    """
    Computes and creates/updates the relationship and nodes
    needed to express the internal peering.
    """
    pass

def insert_external_bgp_peering(peering, service_node):
    """
    Computes and creates/updates the relationship and nodes
    needed to express the external peering.
    """
    # Get or create the peering partner, unique per AS
    peeringp_node = get_peering_partner(peering)
    # Get all relationships with this ip address, should never be more than one
    peeringp_ip = peering.get('remote_address', None)
    if not peeringp_ip:
        peeringp_ip = '0.0.0.0'
    rel_index = nc.get_relationship_index(nc.neo4jdb, nc.search_index_name())
    q = Q('ip_address', '%s' % peeringp_ip)
    peeringp_rel = rel_index.query(str(q))
    peeringp_rel = list(peeringp_rel)
    # See if we already have created this peering relationship
    if peeringp_rel:
        h.set_noclook_auto_manage(nc.neo4jdb, list(peeringp_rel)[0], True)
    else:
        # Create a relationship if couldn't find it
        peeringp_rel = nc.create_relationship(nc.neo4jdb,
                                                       peeringp_node,
                                                       service_node, 'Uses')
        h.set_noclook_auto_manage(nc.neo4jdb, peeringp_rel, True)
        with nc.neo4jdb.transaction:
            peeringp_rel['ip_address'] = peeringp_ip
        # Add the relationship IP address to search index
        h.update_relationship_search_index(nc.neo4jdb, peeringp_rel)
    # Match the remote address against a local network
    remote_addr = ipaddr.IPAddress(peeringp_ip)
    unit_node, local_address = match_remote_ip_address(remote_addr)
    if unit_node and local_address:
        # Check that only one relationship per local address exists
        rels = nc.get_relationships(service_node, unit_node, 'Depends_on')
        for rel in rels:
            if rel['ip_address'] == local_address:
                h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
                return
        # No relationship was found, create one
        with nc.neo4jdb.transaction:
            rel = nc.create_relationship(nc.neo4jdb, service_node, unit_node, 'Depends_on')
            h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
            rel['ip_address'] = local_address
            h.update_relationship_search_index(nc.neo4jdb, rel)

def insert_juniper_bgp_peerings(bgp_peerings):
    """
    Inserts all BGP peerings for all routers collected by the
    juniper_conf producer. This is to be able to get all the internal
    peerings associated to the right interfaces.
    Returns a list of all created peering nodes.
    """
    for peering in bgp_peerings:
        ip_service = peering.get('group', 'Unknown IP Service')
        ip_service_handle = nt.get_unique_node_handle(nc.neo4jdb, ip_service, 
                                                   'IP Service', 'logical')
        ip_service_node = ip_service_handle.get_node()
        h.set_noclook_auto_manage(nc.neo4jdb, ip_service_node, True)
        peering_type = peering.get('type')
        if peering_type == 'internal':
            continue # We said that we should ignore internal peerings, right?
        elif peering_type == 'external':
            insert_external_bgp_peering(peering, ip_service_node)

def consume_juniper_conf(json_list):
    """
    Inserts the data loaded from the json files created by the nerds
    producer juniper_conf.
    Some filtering is done for interface names that are not interesting.
    """
    bgp_peerings = []
    for i in json_list:
        name = i['host']['juniper_conf']['name']
        router_node = insert_juniper_router(name)
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
    args = parser.parse_args()
    # Load the configuration file
    if not args.C:
        print 'Please provide a configuration file with -C.'
        sys.exit(1)
    else:
        config = nt.init_config(args.C)
    if config.get('data', 'juniper_conf'):
        consume_juniper_conf(nt.load_json(config.get('data', 'juniper_conf')))
    return 0

if __name__ == '__main__':
    main()
