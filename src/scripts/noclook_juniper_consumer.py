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
import logging

## Need to change this path depending on where the Django project is
## located.
base_path = '../niweb/'
sys.path.append(os.path.abspath(base_path))
niweb_path = os.path.join(base_path, 'niweb')
sys.path.append(os.path.abspath(niweb_path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import noclook_consumer as nt
from apps.noclook import helpers
from apps.noclook import activitylog
import norduniclient as nc

logger = logging.getLogger('noclook_consumer.juniper')

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

PEER_AS_CACHE = {}
REMOTE_IP_MATCH_CACHE = {}


def insert_juniper_router(name, model, version):
    """
    Inserts a physical meta type node of the type Router.
    Returns the node created.
    """
    logger.info('Processing {name}...'.format(name=name))
    user = nt.get_user()
    node_handle = nt.get_unique_node_handle(name, 'Router', 'Physical')
    node = node_handle.get_node()
    node_dict = {
        'name': name,
        'model': model,
        'version': version
    }
    helpers.dict_update_node(user, node.handle_id, node_dict, node_dict.keys())
    helpers.set_noclook_auto_manage(node, True)
    return node


def insert_interface_unit(iface_node, unit):
    """
    Creates or updates logical interface units.
    """
    user = nt.get_user()
    unit_name = unicode(unit['unit'])
    # Unit names are unique per interface
    result = iface_node.get_unit(unit_name)
    if result.get('Part_of', None):
        unit_node = result.get('Part_of')[0].get('node')
    else:
        node_handle = nt.create_node_handle(unit_name, 'Unit', 'Logical')
        unit_node = node_handle.get_node()
        helpers.set_part_of(user, iface_node, unit_node.handle_id)
        logger.info('Unit {interface}.{unit} created.'.format(interface=iface_node.data['name'],
                                                              unit=unit_node.data['name']))
    helpers.set_noclook_auto_manage(unit_node, True)
    unit['ip_addresses'] = [address.lower() for address in unit.get('address', '')]
    property_keys = ['description', 'ip_addresses', 'vlanid']
    helpers.dict_update_node(user, unit_node.handle_id, unit, property_keys)


def insert_juniper_interfaces(router_node, interfaces):
    """
    Insert all interfaces in the interfaces list with a Has
    relationship from the router_node. Some filtering is done for
    interface names that are not interesting.
    """
    p = """
        .*\*|\.|all|tap|fxp.*|pfe.*|pfh.*|mt.*|pd.*|pe.*|vt.*|bcm.*|dsc.*|em.*|gre.*|ipip.*|lsi.*|mtun.*|pimd.*|pime.*|
        pp.*|pip.*|irb.*|demux.*|cbp.*|me.*|lo.*
        """
    not_interesting_interfaces = re.compile(p, re.VERBOSE)
    user = nt.get_user()
    for interface in interfaces:
        port_name = interface['name']
        if port_name and not not_interesting_interfaces.match(port_name):
            result = router_node.get_port(port_name)
            if result.get('Has', None):
                port_node = result.get('Has')[0].get('node')
            else:
                node_handle = nt.create_node_handle(port_name, 'Port', 'Physical')
                port_node = node_handle.get_node()
                helpers.set_has(user, router_node, port_node.handle_id)
            helpers.set_noclook_auto_manage(port_node, True)
            property_keys = ['description']
            helpers.dict_update_node(user, port_node.handle_id, interface, property_keys)
            # Update interface units
            for unit in interface['units']:
                insert_interface_unit(port_node, unit)
            logger.info('{router} {interface} done.'.format(router=router_node.data['name'], interface=port_name))
        else:
            logger.info('Interface {name} ignored.'.format(name=port_name))


def get_peering_partner(peering):
    """
    Inserts a new node of the type Peering partner and ensures that this node
    is unique for AS number.
    Returns the created node.
    """
    try:
        return PEER_AS_CACHE[peering['as_number']]
    except KeyError:
        logger.info('Peering Partner {name} not in cache.'.format(name=peering.get('description')))
        pass
    user = nt.get_user()
    peer_node = None
    peer_properties = {
        'name':  'Missing description',
        'as_number': '0'
    }
    if peering.get('description'):
        peer_properties['name'] = peering.get('description')
    if peering.get('as_number'):
        peer_properties['as_number'] = peering.get('as_number')
    hits = nc.legacy_node_index_search(nc.neo4jdb, 'as_number: {as_number}'.format(
        as_number=peer_properties.get('as_number')))
    if len(hits['result']) > 1:
        logger.error('Found more then one Peering Partner with AS number {as_number}'.format(
            peer_properties['as_number']))
        logger.error('The following handle ids where found : {ids}'.format(ids=hits['result']))
    for handle_id in hits['result']:
        peer_node = nc.get_node_model(nc.neo4jdb, handle_id)
        helpers.set_noclook_auto_manage(peer_node, True)
        if peer_node.data['name'] == 'Missing description' and peer_properties['name'] != 'Missing description':
            helpers.dict_update_node(user, peer_node.handle_id, peer_properties, peer_properties.keys())
        logger.info('Peering Partner {name} fetched.'.format(name=peer_properties['name']))
    if not peer_node:
        node_handle = nt.create_node_handle(peer_properties['name'], 'Peering Partner', 'Relation')
        peer_node = node_handle.get_node()
        helpers.set_noclook_auto_manage(peer_node, True)
        helpers.dict_update_node(user, peer_node.handle_id, peer_properties, peer_properties.keys())
        logger.info('Peering Partner {name} created.'.format(name=peer_properties['name']))
    PEER_AS_CACHE[peering['as_number']] = peer_node
    return peer_node


def match_remote_ip_address(remote_address):
    """
    Matches a remote address to a local interface.
    Returns a Unit node if match found or else None.
    """
    q = """
        START n=node:node_auto_index({lucene_query})
        RETURN n.handle_id as handle_id, n.ip_addresses as ip_addresses
        """
    # Check cache
    for local_network in REMOTE_IP_MATCH_CACHE.keys():
        if remote_address in local_network:
            cache_hit = REMOTE_IP_MATCH_CACHE[local_network]
            return cache_hit['local_network_node'], cache_hit['address']
    # No cache hit
    for prefix in [3, 2, 1]:
        if remote_address.version == 4:
            mask = '.'.join(str(remote_address).split('.')[0:prefix])
        elif remote_address.version == 6:
            mask = ':'.join(str(remote_address).split(':')[0:prefix])
        lucene_q = unicode(Q('ip_addresses', '%s*' % mask, wildcard=True))
        for hit in nc.query_to_list(nc.neo4jdb, q, lucene_query=lucene_q):
            for address in hit['ip_addresses']:
                try:
                    local_network = ipaddr.IPNetwork(address)
                except ValueError:
                    continue  # ISO address
                if remote_address in local_network:
                    # add local_network, address and node to cache
                    local_network_node = nc.get_node_model(nc.neo4jdb, hit['handle_id'])
                    REMOTE_IP_MATCH_CACHE[local_network] = {
                        'address': address, 'local_network_node': local_network_node
                    }
                    logger.info('Remote IP matched: {name} {ip_address} done.'.format(
                        name=local_network_node.data['name'], ip_address=address))
                    return local_network_node, address
    logger.info('No local IP address matched for {remote_address}.'.format(remote_address=remote_address))
    return None, None


def insert_internal_bgp_peering(peering, service_node):
    """
    Creates/updates the relationship and nodes needed to express the internal peerings.
    """
    pass


def insert_external_bgp_peering(peering, peering_group):
    """
    Creates/updates the relationship and nodes needed to express the external peerings.
    """
    user = nt.get_user()
    # Get or create the peering partner, unique per AS
    peer_node = get_peering_partner(peering)
    # Get all relationships with this ip address, should never be more than one
    remote_address = peering.get('remote_address', None).lower()
    if remote_address:
        # DEBUG
        try:
            result = peer_node.get_peering_group(peering_group.handle_id, remote_address)
        except AttributeError:
            print peer_node
            sys.exit(1)
        if not result.get('Uses'):
            result = peer_node.set_peering_group(peering_group.handle_id, remote_address)
        relationship_id = result.get('Uses')[0]['relationship_id']
        relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
        activitylog.create_relationship(user, relationship)
        helpers.set_noclook_auto_manage(relationship, True)
        if result.get('Uses')[0].get('created', False):
            activitylog.create_relationship(user, relationship)
        # Match the remote address against a local network
        dependency_node, local_address = match_remote_ip_address(ipaddr.IPAddress(remote_address))
        if dependency_node and local_address:
            result = peering_group.get_group_dependency(dependency_node.handle_id, local_address)
            if not result.get('Depends_on'):
                result = peering_group.set_group_dependency(dependency_node.handle_id, local_address)
            relationship_id = result.get('Depends_on')[0]['relationship_id']
            relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
            helpers.set_noclook_auto_manage(relationship, True)
            if result.get('Depends_on')[0].get('created', False):
                activitylog.create_relationship(user, relationship)
        logger.info('Peering Partner {name} done.'.format(name=peer_node.data['name']))


def insert_juniper_bgp_peerings(bgp_peerings):
    """
    Inserts all BGP peerings for all routers collected by the juniper_conf producer.
    This is to be able to get all the peerings associated to the right interfaces.
    """
    for peering in bgp_peerings:
        peering_group = peering.get('group', 'Unknown Peering Group')
        peering_group_handle = nt.get_unique_node_handle(peering_group, 'Peering Group', 'Logical')
        peering_group_node = peering_group_handle.get_node()
        helpers.set_noclook_auto_manage(peering_group_node, True)
        peering_type = peering.get('type')
        if peering_type == 'internal':
            continue  # Not implemented
        elif peering_type == 'external':
            insert_external_bgp_peering(peering, peering_group_node)


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


def remove_router_conf(user, data_age):
    routerq = """
        MATCH (router:Node:Router)
        OPTIONAL MATCH (router)-[:Has*1..]->(physical)<-[:Part_of]-(logical)
        WHERE (physical.noclook_auto_manage = true) OR (logical.noclook_auto_manage = true)
        RETURN collect(distinct physical.handle_id) as physical, collect(distinct logical.handle_id) as logical
        """
    router_result = nc.query_to_dict(nc.neo4jdb, routerq)
    for handle_id in router_result.get('logical', []):
        logical = nc.get_node_model(nc.neo4jdb, handle_id)
        if logical:
            last_seen, expired = helpers.neo4j_data_age(logical.data, data_age)
            if expired:
                helpers.delete_node(user, logical.handle_id)
                logger.info('Deleted node {handle_id}.'.format(handle_id=handle_id))
    for handle_id in router_result.get('physical', []):
        physical = nc.get_node_model(nc.neo4jdb, handle_id)
        if physical:
            last_seen, expired = helpers.neo4j_data_age(physical.data, data_age)
            if expired:
                helpers.delete_node(user, physical.handle_id)
                logger.info('Deleted node {handle_id}.'.format(handle_id=handle_id))


def remove_peer_conf(user, data_age):
    peerq = """
        MATCH (peer_group:Node:Peering_Group)
        MATCH (peer_group)<-[r:Uses]-(peering_partner:Peering_Partner)
        WHERE (peer_group.noclook_auto_manage = true) OR (r.noclook_auto_manage = true)
        RETURN collect(distinct peer_group.handle_id) as peer_groups, collect(id(r)) as uses_relationships
        """
    peer_result = nc.query_to_dict(nc.neo4jdb, peerq)

    for relationship_id in peer_result.get('uses_relationships', []):
        relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
        if relationship:
            last_seen, expired = helpers.neo4j_data_age(relationship.data, data_age)
            if expired:
                helpers.delete_relationship(user, relationship.id)
                logger.info('Deleted relationship {relationship_id}'.format(relationship_id=relationship_id))
    for handle_id in peer_result.get('peer_groups', []):
        peer_group = nc.get_node_model(nc.neo4jdb, handle_id)
        if peer_group:
            last_seen, expired = helpers.neo4j_data_age(peer_group.data, data_age)
            if expired:
                helpers.delete_node(user, peer_group.handle_id)
                logger.info('Deleted node {handle_id}.'.format(handle_id=handle_id))


def remove_juniper_conf(data_age):
    """
    :param data_age: Data older than this many days will be deleted.
    :return: None
    """
    user = nt.get_user()
    data_age = int(data_age) * 24  # hours in a day
    logger.info('Deleting expired router nodes and sub equipment nodes:')
    remove_router_conf(user, data_age)
    logger.info('...done!')
    logger.info('Deleting expired peering partner nodes and relationships:')
    remove_peer_conf(user, data_age)
    logger.info('...done!')


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
        logger.setLevel(logging.INFO)
    if config.get('data', 'juniper_conf'):
        consume_juniper_conf(nt.load_json(config.get('data', 'juniper_conf')))
    if config.getboolean('delete_data', 'juniper_conf'):
        remove_juniper_conf(config.get('data_age', 'juniper_conf'))
    return 0

if __name__ == '__main__':
    logger.setLevel(logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    main()
