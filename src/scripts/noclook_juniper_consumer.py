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

import sys
import re
import argparse
import ipaddress
import logging
import json
import utils

from apps.noclook import helpers
from apps.noclook import activitylog
import norduniclient as nc
from dynamic_preferences.registries import global_preferences_registry
from apps.noclook.models import UniqueIdGenerator, NodeHandle

logger = logging.getLogger('noclook_consumer.juniper')

# This script is used for adding the objects collected with the
# NERDS producers juniper_config to the NOCLook database viewer.
#
# JSON format used:
# {["host": {
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
# ]}

PEER_AS_CACHE = {}
REMOTE_IP_MATCH_CACHE = {}


def insert_juniper_node(name, model, version, node_type='Router', hardware=None):
    """
    Inserts a physical meta type node of the type Router.
    Returns the node created.
    """
    logger.info('Processing {name}...'.format(name=name))
    user = utils.get_user()
    node_handle = utils.get_unique_node_handle(name, node_type, 'Physical')
    node = node_handle.get_node()
    node_dict = {
        'name': name,
        'model': model,
        'version': version
    }
    if hardware:
        node_dict['serial_number'] = hardware.get('serial_number')

    helpers.dict_update_node(user, node.handle_id, node_dict, node_dict.keys())
    helpers.set_noclook_auto_manage(node, True)
    return node


def insert_interface_unit(iface_node, unit, service_id_regex):
    """
    Creates or updates logical interface units.
    """
    user = utils.get_user()
    unit_name = u'{}'.format(unit['unit'])
    # Unit names are unique per interface
    result = iface_node.get_unit(unit_name)
    if result.get('Part_of', None):
        unit_node = result.get('Part_of')[0].get('node')
    else:
        node_handle = utils.create_node_handle(unit_name, 'Unit', 'Logical')
        unit_node = node_handle.get_node()
        helpers.set_part_of(user, iface_node, unit_node.handle_id)
        logger.info('Unit {interface}.{unit} created.'.format(interface=iface_node.data['name'],
                                                              unit=unit_node.data['name']))
    helpers.set_noclook_auto_manage(unit_node, True)
    unit['ip_addresses'] = [address.lower() for address in unit.get('address', '')]
    property_keys = ['description', 'ip_addresses', 'vlanid']
    helpers.dict_update_node(user, unit_node.handle_id, unit, property_keys)
    # Auto depend service on unit
    auto_depend_services(unit_node.handle_id, unit.get('description', ''), service_id_regex, 'Unit')


def cleanup_hardware_v1(router_node, user):
    p = r"^\d+/\d+/\d+$"
    bad_interfaces = re.compile(p)

    # Cleanup ni hardware info v1...
    # Get all ports that are not directly on router
    q = """
        MATCH (n:Router {handle_id: {handle_id}})-[:Has*1..3]->(:Node)-[r:Has]->(port:Port)
        RETURN port.handle_id as handle_id, port.name as name, id(r) as rel_id
        """
    ports = nc.query_to_list(nc.graphdb.manager, q, handle_id=router_node.handle_id)
    for port in ports:
        if bad_interfaces.match(port['name']):
            # delete it!
            helpers.delete_node(user, port['handle_id'])
        else:
            # move it to router
            helpers.set_has(user, router_node, port['handle_id'])
            # Remove from hardware info (pic)
            helpers.delete_relationship(user, port['rel_id'])
            # Scrub interface properties..?
    # Remove hardware info
    q = """
        MATCH (n:Router {handle_id: {handle_id}})-[:Has*]->(hw:Node)
        WHERE NOT hw:Port
        return hw.handle_id as handle_id, hw.name as name
        """
    old_hardware = nc.query_to_list(nc.graphdb.manager, q, handle_id=router_node.handle_id)
    for hw in old_hardware:
        helpers.delete_node(user, hw['handle_id'])


def _service_id_regex():
    global_preferences = global_preferences_registry.manager()
    service_id_generator_name = global_preferences.get('id_generators__services')
    regex = None
    if service_id_generator_name:
        try:
            id_generator = UniqueIdGenerator.objects.get(name=service_id_generator_name)
            regex = id_generator.get_regex()
        except UniqueIdGenerator.DoesNotExist:
            pass
    return regex


def _find_service(service_id):
    # Consider using cypher...
    service = None
    try:
        service = nc.get_unique_node_by_name(nc.graphdb.manager, service_id, 'Service')
    except Exception:
        pass
    return service


def auto_depend_services(handle_id, description, service_id_regex, _type="Port"):
    """
        Using interface description to depend one or more services.
    """
    if not service_id_regex:
        return
    if not description:
        description = ""

    desc_services = service_id_regex.findall(description)

    for service_id in desc_services:
        service = _find_service(service_id)
        if service:
            if service.data.get('operational_state') == 'Decommissioned':
                logger.warning('{} {} description mentions decommissioned service {}'.format(_type, handle_id, service_id))
            else:
                # Add it
                # logger.warning('Service {} should depend on port {}'.format(service_id, handle_id))
                helpers.set_depends_on(utils.get_user(), service, handle_id)
        else:
            logger.info('{} {} description mentions unknown service {}'.format(_type, handle_id, service_id))
    # check if "other services are dependent"
    q = """
        MATCH (n:Node {handle_id: {handle_id}})<-[:Depends_on]-(s:Service)
        WHERE s.operational_state <> 'Decommissioned' and  NOT(s.name in [{desc_services}])
        RETURN collect(s) as unregistered
        """
    result = nc.query_to_dict(nc.graphdb.manager, q, handle_id=handle_id, desc_services=','.join(desc_services)).get('unregistered', [])
    unregistered_services = [u"{}({})".format(s['name'], s['handle_id']) for s in result]

    if unregistered_services:
        logger.info(u"{} {} has services depending on it that is not in description: {}".format(_type, handle_id, ','.join(unregistered_services)))


def insert_juniper_interfaces(router_node, interfaces):
    """
    Insert all interfaces in the interfaces list with a Has
    relationship from the router_node. Some filtering is done for
    interface names that are not interesting.
    """
    p = r"""
        .*\*|\.|all|tap|fxp.*|pfe.*|pfh.*|mt.*|pd.*|pe.*|vt.*|bcm.*|dsc.*|em.*|gre.*|ipip.*|lsi.*|mtun.*|pimd.*|pime.*|
        pp.*|pip.*|irb.*|demux.*|cbp.*|me.*|lo.*
        """
    not_interesting_interfaces = re.compile(p, re.VERBOSE)
    user = utils.get_user()

    cleanup_hardware_v1(router_node, user)
    service_id_regex = _service_id_regex()

    for interface in interfaces:
        port_name = interface['name']
        if port_name and not not_interesting_interfaces.match(port_name) and not interface.get('inactive', False):
            result = router_node.get_port(port_name)
            if 'Has' in result:
                port_node = result.get('Has')[0].get('node')
            else:
                node_handle = utils.create_node_handle(port_name, 'Port', 'Physical')
                port_node = node_handle.get_node()
                helpers.set_has(user, router_node, port_node.handle_id)
            helpers.set_noclook_auto_manage(port_node, True)
            property_keys = ['description', 'name']
            helpers.dict_update_node(user, port_node.handle_id, interface, property_keys)
            # Update interface units
            for unit in interface['units']:
                if not unit.get('inactive', False):
                    insert_interface_unit(port_node, unit, service_id_regex)
            # Auto depend services
            auto_depend_services(port_node.handle_id, interface.get('description', ''), service_id_regex)
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
    user = utils.get_user()
    peer_node = None
    peer_properties = {
        'name': 'Missing description',
        'as_number': '0'
    }
    # neither description or as_number error and return
    if not (peering.get('description') or peering.get('as_number')):
        logger.error('Neither AS number nor description in peering %s', peering)
        return None
    if peering.get('description'):
        peer_properties['name'] = peering.get('description')
    if peering.get('as_number'):
        peer_properties['as_number'] = peering.get('as_number')
        # as number is most important
        hits = nc.get_nodes_by_value(nc.graphdb.manager, prop='as_number', value=peer_properties['as_number'])
        found = 0
        for node in hits:
            peer_node = nc.get_node_model(nc.graphdb.manager, node['handle_id'])
            helpers.set_noclook_auto_manage(peer_node, True)
            if peer_node.data['name'] == 'Missing description' and peer_properties['name'] != 'Missing description':
                helpers.dict_update_node(user, peer_node.handle_id, peer_properties)
            logger.info('Peering Partner {name} fetched.'.format(name=peer_properties['name']))
            found += 1
        if found > 1:
            logger.error('Found more then one Peering Partner with AS number {!s}'.format(peer_properties['as_number']))

        if not peer_node:
            # since we have a AS number we will create a new Peering Partner, even if name is missing or exists
            node_handle = utils.create_node_handle(peer_properties['name'], 'Peering Partner', 'Relation')
            peer_node = node_handle.get_node()
            helpers.set_noclook_auto_manage(peer_node, True)
            helpers.dict_update_node(user, peer_node.handle_id, peer_properties, peer_properties.keys())
            logger.info('Peering Partner %s AS(%s) created.', peer_properties['name'], peer_properties['as_number'])

    # Handle peer with name only
    if not peer_node and peering.get('description'):
        # Try and get peer_partners
        res = NodeHandle.objects.filter(node_name__iexact=peer_properties['name'], node_type__type='Peering Partner').order_by('-modified')
        for ph in res:
            peer_node = ph.get_node()
            break
        if not peer_node:
            # create
            peer_nh = utils.get_unique_node_handle(peer_properties['name'], 'Peering Partner', 'Relation')
            peer_node = peer_nh.get_node()
        if not peer_node.data.get('as_number'):
            # Peering partner did not exist
            logger.warning('Peering Partner %s without AS number created for peering: %s', peer_node.data.get('name'), peering)
            # AS number is going to be 0, but that is ok
            helpers.dict_update_node(user, peer_node.handle_id, peer_properties, peer_properties.keys())

        elif peer_node.data.get('as_number') != '0':
            # warn about as number not being in peering
            logger.warning('Peering found for Peering Partner %s without the AS number %s mentioned. Peering: %s', peer_properties['name'], peer_node.data.get('as_number'), peering)
        helpers.set_noclook_auto_manage(peer_node, True)

    PEER_AS_CACHE[peering['as_number']] = peer_node
    return peer_node


def match_remote_ip_address(remote_address):
    """
    Matches a remote address to a local interface.
    Returns a Unit node if match found or else None.
    """
    # Check cache
    for local_network in REMOTE_IP_MATCH_CACHE.keys():
        if remote_address in local_network:
            cache_hit = REMOTE_IP_MATCH_CACHE[local_network]
            return cache_hit['local_network_node'], cache_hit['address']

    # No cache hit
    mask = None
    for prefix in [3, 2, 1]:
        if remote_address.version == 4:
            mask = '.'.join(str(remote_address).split('.')[0:prefix])
        elif remote_address.version == 6:
            mask = ':'.join(str(remote_address).split(':')[0:prefix])
        if mask:
            mask = '{!s}{!s}'.format(mask, '.*')
        q = '''
            MATCH (n:Unit)
            USING SCAN n:Unit
            WHERE any(x IN n.ip_addresses WHERE x =~ {mask})
            RETURN distinct n
            '''
        for hit in nc.query_to_list(nc.graphdb.manager, q, mask=mask):
            for address in hit['n']['ip_addresses']:
                try:
                    local_network = ipaddress.ip_network(address, strict=False)
                except ValueError:
                    continue  # ISO address
                if remote_address in local_network:
                    # add local_network, address and node to cache
                    local_network_node = nc.get_node_model(nc.graphdb.manager, hit['n']['handle_id'])
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
    user = utils.get_user()
    # Get or create the peering partner, unique per AS
    peer_node = get_peering_partner(peering)
    if peer_node is None:
        # We are done. This is a broken peering.
        return
    # Get all relationships with this ip address, should never be more than one
    remote_address = peering.get('remote_address', None).lower()
    if remote_address:
        # DEBUG
        try:
            result = peer_node.get_peering_group(peering_group.handle_id, remote_address)
        except AttributeError:
            print(peer_node)
            sys.exit(1)
        if not result.get('Uses'):
            result = peer_node.set_peering_group(peering_group.handle_id, remote_address)
        relationship_id = result.get('Uses')[0]['relationship_id']
        relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
        helpers.set_noclook_auto_manage(relationship, True)
        if result.get('Uses')[0].get('created', False):
            activitylog.create_relationship(user, relationship)
        # Match the remote address against a local network
        dependency_node, local_address = match_remote_ip_address(ipaddress.ip_address(remote_address))
        if dependency_node and local_address:
            result = peering_group.get_group_dependency(dependency_node.handle_id, local_address)
            if not result.get('Depends_on'):
                result = peering_group.set_group_dependency(dependency_node.handle_id, local_address)
            relationship_id = result.get('Depends_on')[0]['relationship_id']
            relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
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
        peering_type = peering.get('type')
        if peering_type == 'internal':
            continue  # Not implemented
        elif peering_type == 'external':
            peering_group = peering.get('group', 'Unknown Peering Group')
            peering_group_handle = utils.get_unique_node_handle(peering_group, 'Peering Group', 'Logical', case_insensitive=False)
            peering_group_node = peering_group_handle.get_node()
            helpers.set_noclook_auto_manage(peering_group_node, True)
            insert_external_bgp_peering(peering, peering_group_node)


def insert_juniper_hardware(router_node, hardware):
    if hardware:
        # Upload hardware info as json file.
        hw_str = json.dumps(hardware)
        name = "{}-hardware.json".format(router_node.data.get('name', 'router'))
        user = utils.get_user()
        # Store it! (or overwrite)
        helpers.attach_as_file(router_node.handle_id, name, hw_str, user, overwrite=True)


def consume_juniper_conf(json_list, is_switches):
    """
    Inserts the data loaded from the json files created by the nerds
    producer juniper_conf.
    Some filtering is done for interface names that are not interesting.
    """
    bgp_peerings = []
    for i in json_list:
        if 'nso_juniper' in i['host']:
            jconf = i['host']['nso_juniper']
        else:
            jconf = i['host']['juniper_conf']
        name = jconf['name']
        version = jconf.get('version', 'Unknown')
        model = jconf.get('model', 'Unknown')
        hardware = jconf.get('hardware')
        if is_switches:
            node_type = 'Switch'
        else:
            node_type = 'Router'
        node = insert_juniper_node(name, model, version, node_type, hardware)
        insert_juniper_hardware(node, hardware)
        interfaces = jconf['interfaces']
        insert_juniper_interfaces(node, interfaces)
        bgp_peerings += jconf['bgp_peerings']
    insert_juniper_bgp_peerings(bgp_peerings)


def remove_router_conf(user, data_age):
    routerq = """
        MATCH (router:Node:Router)
        OPTIONAL MATCH (router)-[:Has*1..]->(physical)<-[:Part_of]-(logical)
        WHERE (physical.noclook_auto_manage = true) OR (logical.noclook_auto_manage = true)
        RETURN collect(distinct physical.handle_id) as physical, collect(distinct logical.handle_id) as logical
        """
    router_result = nc.query_to_dict(nc.graphdb.manager, routerq)
    for handle_id in router_result.get('logical', []):
        logical = nc.get_node_model(nc.graphdb.manager, handle_id)
        if logical:
            last_seen, expired = helpers.neo4j_data_age(logical.data, data_age)
            if expired:
                helpers.delete_node(user, logical.handle_id)
                logger.warning('Deleted logical router: %s (%s).', logical.data.get('name'), handle_id)
    for handle_id in router_result.get('physical', []):
        physical = nc.get_node_model(nc.graphdb.manager, handle_id)
        if physical:
            last_seen, expired = helpers.neo4j_data_age(physical.data, data_age)
            if expired:
                helpers.delete_node(user, physical.handle_id)
                logger.warning('Deleted physical router: %s (%s).', physical.data.get('name'), handle_id)


def remove_peer_conf(user, data_age):
    peerq = """
        MATCH (peer_group:Node:Peering_Group)
        MATCH (peer_group)<-[r:Uses]-(peering_partner:Peering_Partner)
        WHERE (peer_group.noclook_auto_manage = true) OR (r.noclook_auto_manage = true)
        RETURN collect(distinct peer_group.handle_id) as peer_groups, collect(id(r)) as uses_relationships
        """
    peer_result = nc.query_to_dict(nc.graphdb.manager, peerq)

    for relationship_id in peer_result.get('uses_relationships', []):
        relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
        if relationship:
            last_seen, expired = helpers.neo4j_data_age(relationship.data, data_age)
            if expired:
                rel_info = helpers.relationship_to_str(relationship)
                helpers.delete_relationship(user, relationship.id)
                logger.warning('Deleted relationship {rel_info}'.format(rel_info=rel_info))
    for handle_id in peer_result.get('peer_groups', []):
        peer_group = nc.get_node_model(nc.graphdb.manager, handle_id)
        if peer_group:
            last_seen, expired = helpers.neo4j_data_age(peer_group.data, data_age)
            if expired:
                helpers.delete_node(user, peer_group.handle_id)
                logger.warning('Deleted node {name} ({handle_id}).'.format(name=peer_group.data.get('name'), handle_id=handle_id))


def remove_juniper_conf(data_age):
    """
    :param data_age: Data older than this many days will be deleted.
    :return: None
    """
    user = utils.get_user()
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
    parser.add_argument('--switches', '-S', action='store_true', default=False, help='Insert as switches rather than routers')
    parser.add_argument('--data', '-d', required=False, help='Directory to load date from. Trumps config file.')
    args = parser.parse_args()
    # Load the configuration file
    if not args.C and not args.data:
        print('Please provide a configuration file with -C or --data for a data directory.')
        sys.exit(1)
    elif not args.data:
        config = utils.init_config(args.C)
    else:
        config = None

    data = args.data or config.get('data', 'juniper_conf')

    if args.verbose:
        logger.setLevel(logging.INFO)
    if data:
        consume_juniper_conf(utils.load_json(data), args.switches)
    if config and config.has_option('delete_data', 'juniper_conf') and config.getboolean('delete_data', 'juniper_conf'):
        remove_juniper_conf(config.get('data_age', 'juniper_conf'))
    return 0


if __name__ == '__main__':
    if not len(logger.handlers):
        logger.propagate = False
        logger.setLevel(logging.WARNING)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    main()
