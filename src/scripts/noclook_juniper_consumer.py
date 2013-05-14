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
from apps.noclook import activitylog
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

VERBOSE = False

def insert_juniper_router(name, model, version):
    """
    Inserts a physical meta type node of the type Router.
    Returns the node created.
    """
    user = nt.get_user()
    node_handle = nt.get_unique_node_handle(nc.neo4jdb, name, 'Router', 
                                            'physical')
    node = node_handle.get_node()
    node_dict = {
        'name': name,
        'model': model,
        'version': version
    }
    h.dict_update_node(user, node, node_dict, node_dict.keys())
    h.set_noclook_auto_manage(nc.neo4jdb, node, True)
    if VERBOSE:
        print 'Processing %s...' % node_handle
    return node

def insert_interface_unit(interf_node, unit):
    """
    Creates or updates logical interface units.
    """
    user = nt.get_user()
    # Unit numbers are unique per interface
    q = """
        START interface=node({id})
        MATCH interface<-[:Part_of]-unit
        WHERE unit.name = {unit_name}
        RETURN unit
        """
    hit = nc.neo4jdb.query(q, id=interf_node.getId(), unit_name=unit['unit']).single
    if hit:
        node = hit['unit']
    else:
        node_handle = nt.get_node_handle(nc.neo4jdb, unit['unit'], 'Unit',
                                         'logical', interf_node)
        node = node_handle.get_node()
    h.set_noclook_auto_manage(nc.neo4jdb, node, True)
    unit['ip_addresses'] = unit.get('address', '')
    property_keys = ['description', 'ip_addresses', 'vlanid']
    h.dict_update_node(user, node, unit, property_keys)
    rels = nc.get_relationships(node, interf_node, 'Part_of')
    if rels:
        for rel in rels:
            h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
    else:
        # Only create a relationship if it doesn't exist
        rel = nc.create_relationship(
            nc.neo4jdb,
            node,
            interf_node,
            'Part_of'
        )
        h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
        activitylog.create_relationship(user, rel)
        if VERBOSE:
            print '%s %s inserted.' % (node['node_type'], node['name'])

def insert_juniper_interfaces(router_node, interfaces):
    """
    Insert all interfaces in the interfaces list with a Has
    relationship from the router_node. Some filtering is done for
    interface names that are not interesting.
    Returns a list with all created nodes.
    """
    not_interesting_interfaces = re.compile(r'.*\*|\.|all|fxp.*|pfe.*|pfh.*|mt.*|pd.*|pe.*|vt.*|bcm.*|dsc.*|em.*|gre.*|ipip.*|lsi.*|mtun.*|pimd.*|pime.*|pp.*|pip.*|irb.*|demux.*|cbp.*|me.*|lo.*')
    for i in interfaces:
        name = i['name']
        if name and not not_interesting_interfaces.match(name):
            node_handle = nt.get_node_handle(nc.neo4jdb, name, 'Port',
                                             'physical', router_node)
            node = node_handle.get_node()
            h.set_noclook_auto_manage(nc.neo4jdb, node, True)
            user = nt.get_user()
            property_keys = ['description']
            h.dict_update_node(user, node, i, property_keys)
            for unit in i['units']:
                insert_interface_unit(node, unit)
            rels = nc.get_relationships(router_node, node, 'Has')
            if rels:
                for rel in rels:
                    h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
                # Only create a relationship if it doesn't exist
            else:
                rel =  nc.create_relationship(
                    nc.neo4jdb,
                    router_node,
                    node,
                    'Has'
                )
                h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
                activitylog.create_relationship(user, rel)
            if VERBOSE:
                print '%s done.' % node_handle
        elif VERBOSE:
                print 'Interface %s ignored.' % name

def get_peering_partner(peering):
    """
    Inserts a new node of the type Peering partner and ensures that this node
    is unique for AS number.
    Returns the created node.
    """
    user = nt.get_user()
    data = {
        'name': peering.get('description', 'Missing description'),
        'as_number': peering.get('as_number', '0')
    }
    # description can be None
    if not data['name']:
        data['name'] = 'Missing description'
    # as_number can be None
    if not data['as_number']:
        data['as_number'] = '0'
    index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
    try:
        node = index['as_number'][data['as_number']][0]
        h.set_noclook_auto_manage(nc.neo4jdb, node, True)
        if node['name'] == 'Missing description':
            property_keys = ['name']
            h.dict_update_node(user, node, data, property_keys)
        if VERBOSE:
            print '%s %s fetched.' % (node['node_type'], node['name'])
    except StopIteration:
        node_handle = nt.get_node_handle(
            nc.neo4jdb,
            data['name'],
            'Peering Partner',
            'relation'
        )
        node = node_handle.get_node()
        h.set_noclook_auto_manage(nc.neo4jdb, node, True)
        property_keys = ['as_number']
        h.dict_update_node(user, node, data, property_keys)
        if VERBOSE:
            print '%s %s inserted.' % (node['node_type'], node['name'])
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
                    if VERBOSE:
                        print 'Remote IP matched: %s %s done.' % (str(hit), str(addr))
                    return hit, addr
    if VERBOSE:
        print 'No IP address matched.'
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
    user = nt.get_user()
    # Get or create the peering partner, unique per AS
    peeringp_node = get_peering_partner(peering)
    # Get all relationships with this ip address, should never be more than one
    peeringp_ip = peering.get('remote_address', '0.0.0.0')
    rel_index = nc.get_relationship_index(nc.neo4jdb, nc.search_index_name())
    q = Q('ip_address', '%s' % peeringp_ip)
    peeringp_rel = rel_index.query(str(q))
    peeringp_rel = list(peeringp_rel)
    # See if we already have created this peering relationship
    if peeringp_rel:
        h.set_noclook_auto_manage(nc.neo4jdb, list(peeringp_rel)[0], True)
    else:
        # Create a relationship if it did not exist
        peeringp_rel = nc.create_relationship(
            nc.neo4jdb,
            peeringp_node,
            service_node,
            'Uses'
        )
        activitylog.create_relationship(user, peeringp_rel)
        rel_dict = {'ip_address': peeringp_ip}
        h.dict_update_relationship(user, peeringp_rel, rel_dict, rel_dict.keys())
        h.set_noclook_auto_manage(nc.neo4jdb, peeringp_rel, True)
    # Match the remote address against a local network
    remote_addr = ipaddr.IPAddress(peeringp_ip)
    unit_node, local_address = match_remote_ip_address(remote_addr)
    if unit_node and local_address:
        # Check that only one relationship per local address exists
        create = True
        rels = nc.get_relationships(service_node, unit_node, 'Depends_on')
        for rel in rels:
            if rel.get_property('ip_address', None) == local_address:
                h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
                create = False
        # No relationship was found, create one
        if create:
            rel = nc.create_relationship(nc.neo4jdb, service_node, unit_node, 'Depends_on')
            h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
            rel_dict = {'ip_address': local_address}
            h.dict_update_relationship(user, rel, rel_dict, rel_dict.keys())
            activitylog.create_relationship(user, rel)
    if VERBOSE:
        print '%s %s done.' % (peeringp_node['node_type'], peeringp_node['name'])

def insert_juniper_bgp_peerings(bgp_peerings):
    """
    Inserts all BGP peerings for all routers collected by the
    juniper_conf producer. This is to be able to get all the internal
    peerings associated to the right interfaces.
    """
    for peering in bgp_peerings:
        ip_service = peering.get('group', 'Unknown Peering Group')
        ip_service_handle = nt.get_unique_node_handle(nc.neo4jdb, ip_service, 
                                                   'Peering Group', 'logical')
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
        version = i['host']['juniper_conf'].get('version', 'Unknown')
        model = i['host']['juniper_conf'].get('model', 'Unknown')
        router_node = insert_juniper_router(name, model, version)
        interfaces = i['host']['juniper_conf']['interfaces']
        insert_juniper_interfaces(router_node, interfaces)
        bgp_peerings += i['host']['juniper_conf']['bgp_peerings']
    insert_juniper_bgp_peerings(bgp_peerings)

def remove_juniper_conf(data_age):
    """
    :param data_age: Data older than this many days will be deleted.
    :return: None
    """
    q = """
        START router=node:node_types(node_type="Router")
        MATCH router-[:Has*1..]->physical<-[?:Part_of]-logical
        WHERE (physical.noclook_auto_manage! = true) OR (logical.noclook_auto_manage! = true)
        WITH distinct physical, logical
        RETURN collect(physical) as physical, collect(logical) as logical
        """
    user = nt.get_user()
    data_age = int(data_age) * 24 # hours in a day
    for hit in nc.neo4jdb.query(q):
        if VERBOSE:
            print 'Deleting expired nodes',
        for logical in hit['logical']:
            last_seen, expired = h.neo4j_data_age(logical, data_age)
            if expired:
                h.delete_node(user, logical)
                if VERBOSE:
                    print '.',
        for physical in hit['physical']:
            last_seen, expired = h.neo4j_data_age(physical, data_age)
            if expired:
                h.delete_node(user, physical)
                if VERBOSE:
                    print '.',

def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?', help='Path to the configuration file.')
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    args = parser.parse_args()
    # Load the configuration file
    if not args.C:
        print 'Please provide a configuration file with -C.'
        sys.exit(1)
    else:
        config = nt.init_config(args.C)
    if args.verbose:
        global VERBOSE
        VERBOSE = True
    if config.get('data', 'juniper_conf'):
        consume_juniper_conf(nt.load_json(config.get('data', 'juniper_conf')))
    if config.getboolean('delete_data', 'juniper_conf'):
        remove_juniper_conf(config.get('data_age', 'juniper_conf'))
    return 0

if __name__ == '__main__':
    main()
