"""
apps/nerds/lib/juniper_consumer.py
===================================
Shared graph-writing logic for the juniper_conf NERDS producer.
consume_juniper_conf() or juniper_import() are the main entry points, providing a list of NERDS dicts or a single NERDS dict, respectively.
Each dict represents a single device, and should have the same structure as the "host" dicts produced by the juniper_conf NERDS producer.
"""

import re
import ipaddress
import json
import logging

from norduni.apps.noclook import helpers, activitylog
from norduni.apps.noclook.models import UniqueIdGenerator, NodeHandle
from norduni.apps.nerds.lib import consumer_util as nlu
import norduni.graphdb as nc
from dynamic_preferences.registries import global_preferences_registry

logger = logging.getLogger('noclook_consumer.juniper')

PEER_AS_CACHE = {}
REMOTE_IP_MATCH_CACHE = {}

def insert_juniper_node(name, model, version, node_type='Router', hardware=None):
    logger.info('Processing {name}...'.format(name=name))
    user = nlu.get_user()
    node_handle = nlu.get_unique_node_handle(name, node_type, 'Physical')
    node = node_handle.get_node()
    node_dict = {'name': name, 'model': model, 'version': version}
    if hardware:
        node_dict['serial_number'] = hardware.get('serial_number')
    helpers.dict_update_node(user, node.handle_id, node_dict, node_dict.keys())
    helpers.set_noclook_auto_manage(node, True)
    return node


def insert_juniper_hardware(router_node, hardware):
    if hardware:
        hw_str = json.dumps(hardware)
        name = '{}-hardware.json'.format(router_node.data.get('name', 'router'))
        user = nlu.get_user()
        helpers.attach_as_file(router_node.handle_id, name, hw_str, user, overwrite=True)

def _service_id_regex():
    global_preferences = global_preferences_registry.manager()
    service_id_generator_name = global_preferences.get('id_generators__services')
    if service_id_generator_name:
        try:
            id_generator = UniqueIdGenerator.objects.get(name=service_id_generator_name)
            return id_generator.get_regex()
        except UniqueIdGenerator.DoesNotExist:
            pass
    return None


def _find_service(service_id):
    try:
        return nc.get_unique_node_by_name(nc.graphdb.manager, service_id, 'Service')
    except Exception:
        return None


def auto_depend_services(handle_id, description, service_id_regex, _type='Port'):
    if not service_id_regex or not description:
        return
    desc_services = service_id_regex.findall(description)
    for service_id in desc_services:
        service = _find_service(service_id)
        if service:
            if service.data.get('operational_state') == 'Decommissioned':
                logger.warning('%s %s description mentions decommissioned service %s', _type, handle_id, service_id)
            else:
                helpers.set_depends_on(nlu.get_user(), service, handle_id)
        else:
            logger.info('%s %s description mentions unknown service %s', _type, handle_id, service_id)
    q = """
        MATCH (n:Node {handle_id: $handle_id})<-[:Depends_on]-(s:Service)
        WHERE s.operational_state <> 'Decommissioned' and NOT(s.name in [$desc_services])
        RETURN collect(s) as unregistered
        """
    result = nc.query_to_dict(nc.graphdb.manager, q, handle_id=handle_id,
                              desc_services=','.join(desc_services)).get('unregistered', [])
    unregistered = [u'{}({})'.format(s['name'], s['handle_id']) for s in result]
    if unregistered:
        logger.info('%s %s has services depending on it not in description: %s', _type, handle_id, ','.join(unregistered))


def insert_interface_unit(iface_node, unit, service_id_regex):
    user = nlu.get_user()
    unit_name = u'{}'.format(unit['unit'])
    result = iface_node.get_unit(unit_name)
    if result.get('Part_of', None):
        unit_node = result.get('Part_of')[0].get('node')
    else:
        node_handle = nlu.create_node_handle(unit_name, 'Unit', 'Logical')
        unit_node = node_handle.get_node()
        helpers.set_part_of(user, iface_node, unit_node.handle_id)
        logger.info('Unit %s.%s created.', iface_node.data['name'], unit_node.data['name'])
    helpers.set_noclook_auto_manage(unit_node, True)
    unit['ip_addresses'] = [address.lower() for address in unit.get('address', '')]
    helpers.dict_update_node(user, unit_node.handle_id, unit, ['description', 'ip_addresses', 'vlanid'])
    auto_depend_services(unit_node.handle_id, unit.get('description', ''), service_id_regex, 'Unit')


def cleanup_hardware_v1(router_node, user):
    bad_interfaces = re.compile(r'^\d+/\d+/\d+$')
    q = """
        MATCH (n:Router {handle_id: $handle_id})-[:Has*1..3]->(:Node)-[r:Has]->(port:Port)
        RETURN port.handle_id as handle_id, port.name as name, id(r) as rel_id
        """
    ports = nc.query_to_list(nc.graphdb.manager, q, handle_id=router_node.handle_id)
    for port in ports:
        if bad_interfaces.match(port['name']):
            helpers.delete_node(user, port['handle_id'])
        else:
            helpers.set_has(user, router_node, port['handle_id'])
            helpers.delete_relationship(user, port['rel_id'])
    q = """
        MATCH (n:Router {handle_id: $handle_id})-[:Has*]->(hw:Node)
        WHERE NOT hw:Port
        return hw.handle_id as handle_id, hw.name as name
        """
    old_hardware = nc.query_to_list(nc.graphdb.manager, q, handle_id=router_node.handle_id)
    for hw in old_hardware:
        helpers.delete_node(user, hw['handle_id'])


def insert_juniper_interfaces(router_node, interfaces):
    p = r"""
        .*\*|\.|all|tap|pfe.*|pfh.*|mt.*|pd.*|pe.*|vt.*|bcm.*|dsc.*|em.*|gre.*|ipip.*|lsi.*|mtun.*|pimd.*|pime.*|
        pp.*|pip.*|irb.*|demux.*|cbp.*|me.*|lo.*
        """
    not_interesting = re.compile(p, re.VERBOSE)
    user = nlu.get_user()
    cleanup_hardware_v1(router_node, user)
    service_id_regex = _service_id_regex()
    for interface in interfaces:
        port_name = interface['name']
        if port_name and not not_interesting.match(port_name) and not interface.get('inactive', False):
            result = router_node.get_port(port_name)
            if 'Has' in result:
                port_node = result.get('Has')[0].get('node')
            else:
                node_handle = nlu.create_node_handle(port_name, 'Port', 'Physical')
                port_node = node_handle.get_node()
                helpers.set_has(user, router_node, port_node.handle_id)
            helpers.set_noclook_auto_manage(port_node, True)
            helpers.dict_update_node(user, port_node.handle_id, interface, ['description', 'name'])
            for unit in interface['units']:
                if not unit.get('inactive', False):
                    insert_interface_unit(port_node, unit, service_id_regex)
            auto_depend_services(port_node.handle_id, interface.get('description', ''), service_id_regex)
            logger.info('%s %s done.', router_node.data['name'], port_name)
        else:
            logger.info('Interface %s ignored.', port_name)

def match_remote_ip_address(remote_address):
    for local_network in REMOTE_IP_MATCH_CACHE.keys():
        if remote_address in local_network:
            cache_hit = REMOTE_IP_MATCH_CACHE[local_network]
            return cache_hit['local_network_node'], cache_hit['address']
    for prefix in [3, 2, 1]:
        if remote_address.version == 4:
            mask = '.'.join(str(remote_address).split('.')[0:prefix]) + '.*'
        else:
            mask = ':'.join(str(remote_address).split(':')[0:prefix]) + '.*'
        q = '''
            MATCH (n:Unit)
            USING SCAN n:Unit
            WHERE any(x IN n.ip_addresses WHERE x =~ $mask)
            RETURN distinct n
            '''
        for hit in nc.query_to_list(nc.graphdb.manager, q, mask=mask):
            for address in hit['n']['ip_addresses']:
                try:
                    local_network = ipaddress.ip_network(address, strict=False)
                except ValueError:
                    continue
                if remote_address in local_network:
                    local_network_node = nc.get_node_model(nc.graphdb.manager, hit['n']['handle_id'])
                    REMOTE_IP_MATCH_CACHE[local_network] = {
                        'address': address, 'local_network_node': local_network_node
                    }
                    logger.info('Remote IP matched: %s %s done.', local_network_node.data['name'], address)
                    return local_network_node, address
    logger.info('No local IP address matched for %s.', remote_address)
    return None, None


def get_peering_partner(peering):
    try:
        return PEER_AS_CACHE[peering['as_number']]
    except KeyError:
        pass
    user = nlu.get_user()
    peer_node = None
    peer_properties = {'name': 'Missing description', 'as_number': '0'}
    if not (peering.get('description') or peering.get('as_number')):
        logger.error('Neither AS number nor description in peering %s', peering)
        return None
    if peering.get('description'):
        peer_properties['name'] = peering['description']
    if peering.get('as_number'):
        peer_properties['as_number'] = peering['as_number']
        hits = nc.get_nodes_by_value(nc.graphdb.manager, prop='as_number', value=peer_properties['as_number'])
        found = 0
        for node in hits:
            peer_node = nc.get_node_model(nc.graphdb.manager, node['handle_id'])
            helpers.set_noclook_auto_manage(peer_node, True)
            if peer_node.data['name'] == 'Missing description' and peer_properties['name'] != 'Missing description':
                helpers.dict_update_node(user, peer_node.handle_id, peer_properties)
            logger.info('Peering Partner %s fetched.', peer_properties['name'])
            found += 1
        if found > 1:
            logger.error('Found more than one Peering Partner with AS number %s', peer_properties['as_number'])
        if not peer_node:
            node_handle = nlu.get_unique_node_handle(peer_properties['name'], 'Peering Partner', 'Relation')
            peer_node = node_handle.get_node()
            helpers.set_noclook_auto_manage(peer_node, True)
            helpers.dict_update_node(user, peer_node.handle_id, peer_properties, peer_properties.keys())
            logger.info('Peering Partner %s AS(%s) created.', peer_properties['name'], peer_properties['as_number'])
    if not peer_node and peering.get('description'):
        res = NodeHandle.objects.filter(
            node_name__iexact=peer_properties['name'],
            node_type__type='Peering Partner'
        ).order_by('-modified')
        for ph in res:
            peer_node = ph.get_node()
            break
        if not peer_node:
            peer_nh = nlu.get_unique_node_handle(peer_properties['name'], 'Peering Partner', 'Relation')
            peer_node = peer_nh.get_node()
        if not peer_node.data.get('as_number'):
            logger.warning('Peering Partner %s without AS number created for peering: %s',
                           peer_node.data.get('name'), peering)
            helpers.dict_update_node(user, peer_node.handle_id, peer_properties, peer_properties.keys())
        elif peer_node.data.get('as_number') != '0':
            logger.warning('Peering found for Peering Partner %s without AS number %s mentioned. Peering: %s',
                           peer_properties['name'], peer_node.data.get('as_number'), peering)
        helpers.set_noclook_auto_manage(peer_node, True)
    PEER_AS_CACHE[peering['as_number']] = peer_node
    return peer_node


def insert_external_bgp_peering(peering, peering_group):
    user = nlu.get_user()
    peer_node = get_peering_partner(peering)
    if peer_node is None:
        return
    remote_address = peering.get('remote_address', None)
    if not remote_address:
        return
    remote_address = remote_address.lower()
    result = peer_node.get_peering_group(peering_group.handle_id, remote_address)
    if not result.get('Uses'):
        result = peer_node.set_peering_group(peering_group.handle_id, remote_address)
    relationship_id = result.get('Uses')[0]['relationship_id']
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
    helpers.set_noclook_auto_manage(relationship, True)
    if result.get('Uses')[0].get('created', False):
        activitylog.create_relationship(user, relationship)
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
    logger.info('Peering Partner %s done.', peer_node.data['name'])


def insert_juniper_bgp_peerings(bgp_peerings):
    for peering in bgp_peerings:
        peering_type = peering.get('type')
        if peering_type == 'internal':
            continue
        elif peering_type == 'external':
            peering_group_name = peering.get('group', 'Unknown Peering Group')
            peering_group_handle = nlu.get_unique_node_handle(
                peering_group_name, 'Peering Group', 'Logical')
            peering_group_node = peering_group_handle.get_node()
            helpers.set_noclook_auto_manage(peering_group_node, True)
            insert_external_bgp_peering(peering, peering_group_node)

def consume_juniper_conf(json_list, is_switches=False):
    """
    Insert/update graph nodes for a list of NERDS dicts produced by
    juniper_conf (or nso_juniper).  Called by both the batch script and
    the inline HTTP consumer.
    """
    bgp_peerings = []
    for i in json_list:
        if 'nso_juniper' in i['host']:
            jconf = i['host']['nso_juniper']
        elif 'juniper_conf' in i['host']:
            jconf = i['host']['juniper_conf']
        else:
            logger.warning('Skipping non-juniper device: %s', i['host'].get('name'))
            continue
        node_type = 'Switch' if is_switches else 'Router'
        name     = jconf['name']
        version  = jconf.get('version', 'Unknown')
        model    = jconf.get('model', 'Unknown')
        hardware = jconf.get('hardware')
        node = insert_juniper_node(name, model, version, node_type, hardware)
        insert_juniper_hardware(node, hardware)
        insert_juniper_interfaces(node, jconf['interfaces'])
        bgp_peerings += jconf['bgp_peerings']
    insert_juniper_bgp_peerings(bgp_peerings)


def juniper_import(nerds_json):
    """Convenience wrapper for a single NERDS dict (on-demand HTTP path)."""
    consume_juniper_conf([nerds_json], is_switches=False)
