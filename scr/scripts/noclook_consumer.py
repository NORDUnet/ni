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
import os
from os.path import join
import json
import datetime
import ConfigParser
import argparse
import ipaddr

## Need to change this path depending on where the Django project is
## located.
path = '/var/norduni/scr/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from apps.noclook.models import NodeType, NodeHandle
from django.contrib.auth.models import User
import neo4jclient

'''
This script is used for adding the objects collected with the
NERDS juniper_conf producer to the noclook database viewer.
'''

def init_config(path):
    '''
    Initializes the configuration file located in the path provided.
    '''
    try:
       config = ConfigParser.SafeConfigParser()
       config.read(path)
       return config
    except IOError as (errno, strerror):
        print "I/O error({0}): {1}".format(errno, strerror)

def test_db():
    handles = NodeHandle.objects.all()
    nc = neo4jclient.Neo4jClient()
    print 'Handle\tNode'
    for handle in handles:
        print '%d\t%s' % (handle.handle_id, nc.get_node_by_id(
            handle.node_id))

def purge_db():
    nc = neo4jclient.Neo4jClient()
    for h in NodeHandle.objects.all():
        nc.delete_node(h.node_id)
    NodeHandle.objects.all().delete()

def get_node_type(type_name):
    '''
    Returns or creates and returns the NodeType object with the supplied
    name.
    '''
    try:
        node_type = NodeType.objects.get(type=type_name)
    except Exception as e:
        print e                                             # Debug
        # The NodeType was not found, create one
        from django.template.defaultfilters import slugify
        node_type = NodeType(type=type_name, slug=slugify(type_name))
        print 'Creating NodeType instance %s' % type_name   # Debug
        node_type.save()

    return node_type

def get_node_handle(node_name, node_type_name, node_meta_type):
    '''
    Takes the arguments as strings.
    Returns a NodeHandle object.
    '''
    # Hard coded user value that we can't get on the fly right now
    user = User.objects.get(username='lundberg')
    node_type = get_node_type(node_type_name)
    try:
        node_handle = NodeHandle.objects.get(node_name=node_name,
                                            node_type=node_type)
        print 'NodeHandle instance found, updating it.' # Debug
    except Exception as e:
        print e                                         # Debug
        # The NodeHandle was not found, create one
        node_handle = NodeHandle(node_name=node_name,
                                node_type=node_type,
                                node_meta_type=node_meta_type,
                                creator=user)
        print 'Creating NodeHandle instance %s.' % node_name    # Debug
        node_handle.save()
    return node_handle

def rest_comp(data):
    '''
    As the REST interface cant handle None type we change None to False.
    '''
    if data is None:
        return False
    else:
        return data

def insert_juniper_router(name):
    '''
    Inserts a physical meta type node of the type Router.
    Returns the node created.
    '''
    nc = neo4jclient.Neo4jClient()
    node_handle = get_node_handle(name, 'Router', 'physical')
    node = nc.get_node_by_id(node_handle.node_id)
    node_list = [node]

    return node_list

def insert_juniper_interfaces(router_node, interfaces):
    '''
    Insert all interfaces in the interfaces list with a Has
    relationship from the router_node. Some filtering is done for
    interface names that are not interesting.
    Returns a list with all created nodes.
    '''
    nc = neo4jclient.Neo4jClient()
    not_interesting_interfaces = ['all', 'fxp0', '']
    node_list = []
    for i in interfaces:
        name = i['name']
        if name not in not_interesting_interfaces:
            # Also "not interesting" is interfaces with . or * in their
            # names
            if '.' not in name and '*' not in name:
                node_handle = get_node_handle(name, 'PIC', 'physical')
                node = nc.get_node_by_id(node_handle.node_id)
                node['description'] = rest_comp(i['description'])
                node['units'] = json.dumps(i['units'])
                router_node.Has(node)
                node_list.append(node)

    return node_list

def insert_juniper_relation(name, as_number):
    '''
    Inserts a relation meta type node of the type Peering partner.
    Returns the newly created node.
    '''
    nc = neo4jclient.Neo4jClient()
    node_handle = get_node_handle(name, 'Peering Partner', 'relation')
    node = nc.get_node_by_id(node_handle.node_id)
    node['as_number'] = rest_comp(as_number)
    node_list = [node]

    return node_list

def insert_juniper_service(name):
    '''
    Inserts a logical meta type node of the type IP Service.
    Returns the newly created node.
    '''
    nc = neo4jclient.Neo4jClient()
    node_handle = get_node_handle(name, 'IP Service', 'logical')
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
    nc = neo4jclient.Neo4jClient()
    node_list = []
    for p in bgp_peerings:
        name = p['description']
        if name == None:
            name = 'No description'

        group = p['group']
        service = nc.get_node_by_value(group, 'logical', 'name')
        if service == []:
            service = insert_juniper_service(group)

        peering_type = p['type']
        if peering_type == 'internal':
            remote_addr = ipaddr.IPAddress(p['remote_address'])
            local_addr = ipaddr.IPAddress(p['local_address'])

        elif peering_type == 'external':
            peeringp = nc.get_node_by_value(name, 'relation', 'name')
            if peeringp == []:
                peeringp = insert_juniper_relation(name, p['as_number'])
            peeringp[0].Uses(service[0], ip_address=p['remote_address'])
            remote_addr = ipaddr.IPAddress(p['remote_address'])
            local_addr = ipaddr.IPAddress('0.0.0.0') #None did not work

        # Loop through interfaces to find the local and/or remote
        # address
        meta_node = nc.get_meta_node('physical')
        node_dict = {}
        for rel in meta_node.relationships.outgoing(["Contains"]):
            if rel.end['type'] == 'PIC':
                units = json.loads(rel.end['units'])
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
                                                rel.end, 'Depends_on')
                            create = True # Create new relation
                            for rel in rels:
                                # Can't have more than one unit with the
                                # same unit number
                                if rel['unit'] == unit['unit']:
                                    create = False  # Do not create a
                                    break           # new relation
                            if create:
                                service[0].Depends_on(rel.end,
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
        interface_nodes = insert_juniper_interfaces(router_node,
                            interfaces)
        bgp_peerings += i['host']['juniper_conf']['bgp_peerings']

    bgp_peering_nodes = insert_juniper_bgp_peerings(bgp_peerings)


def insert_nmap(json_list):
    '''
    Inserts the data loaded from the json files created by
    the nerds producer nmap_services.
    '''
    nc = neo4jclient.Neo4jClient()

    # Hard coded values that we can't get on the fly right now
    #user = User.objects.get(username="lundberg")
    node_type = "Host"
    meta_type = 'physical'

    # Insert the host
    for i in json_list:
        name = i['host']['name']
        hostnames = json.dumps(i['host']['hostnames'])
        addresses = json.dumps(i['host']['addrs'])
        try:
            services = json.dumps(i['host']['services'])
        except KeyError:
            services = 'None'

        # Create the NodeHandle and the Node
        node_handle = get_node_handle(name, node_type, meta_type)
        #node_handle = NodeHandle(node_name=name, node_type=type,
            #node_meta_type = meta_type, creator=user)
        #node_handle.save()

        # Set Node attributes
        node = nc.get_node_by_id(node_handle.node_id)
        node['hostnames'] = hostnames
        node['addresses'] = addresses
        node['services'] = services

def insert_cable(cable_id, cable_type):
    '''
    Creates a new cable node and node_handle.
    Returns the node in a node_list.
    '''
    nc = neo4jclient.Neo4jClient()
    node_handle = get_node_handle(cable_id, 'Cable', 'physical')
    node = nc.get_node_by_id(node_handle.node_id)
    node['cable_type'] = cable_type
    return node_handle

def consume_alcatel_isis(json_list):
    '''
    Inserts the data loaded from the json files created by the nerds
    producer alcatel_isis.

    Metric = 0      "localhost"
    Metric = 12     "LAN connected"
    Metric = 19     "OMS - optical multiplex section connection"
                    (between LM's only)
    Metric = 20/21  "direct fiber connection"
    '''
    nc = neo4jclient.Neo4jClient()

    # Insert the optical node
    for i in json_list:
        name = i['host']['name']
        node_handle = get_node_handle(name, 'Optical Node', 'physical')
        node = nc.get_node_by_id(node_handle.node_id)
        for neighbour in i['host']['alcatel_isis']['neighbours']:
            metric = neighbour['metric']
            if metric == '0':       # localhost
                break
            elif metric == '12':    # LAN connected
                cable_type = 'TP'
            else:                   # Fiber
                cable_type = 'Fiber'
            # Get or create a neighbour node
            neighbour_node_handle = get_node_handle(neighbour['name'],
                                            'Optical Node', 'physical')
            neighbour_node = nc.get_node_by_id(neighbour_node_handle.node_id)
            # See if the nodes already are connected via something
            create = True
            for rel in node.relationships.incoming(['Connected_to']):
                for rel2 in rel.start.relationships.outgoing(['Connected_to']):
                    if rel2.end['name'] == neighbour_node['name']:
                        create = False
                        break
            if create:
                tmp_name = '%s - %s' % (node['name'], neighbour_node['name']) # Is this good until we get the fiber id?
                cable_handle = insert_cable(tmp_name, cable_type)
                cable_node = nc.get_node_by_id(cable_handle.node_id)
                cable_node.Connected_to(node)
                cable_node.Connected_to(neighbour_node)

def load_json(json_dir):
    '''
    Thinks all files in the supplied dir are text files containing json.
    '''
    json_list = []

    for subdir, dirs, files in os.walk(json_dir):
        for file in files:
            f=open(join(json_dir, file), 'r')
            json_list.append(json.load(f))

    return json_list

def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?',
        help='Path to the configuration file.')
    parser.add_argument('-P', action='store_true',
        help='Purge the database.')
    parser.add_argument('-I', action='store_true',
        help='Insert data in to the database.')
    parser.add_argument('-T', action='store_true',
        help='Test the database database setup.')
    args = parser.parse_args()

    # Test DB connection
    if args.T:
        test_db()
        sys.exit(0)

    # Load the configuration file
    if args.C == None:
        print 'Please provide a configuration file with -C.'
        sys.exit(1)
    else:
        config = init_config(args.C)

    # Purge DB if option -P was used
    if args.P:
        print 'Purging database...'
        purge_db()

    # Insert data from known data sources if option -I was used
    if args.I:
        print 'Inserting data...'
        if config.get('data', 'juniper_conf'):
            consume_juniper_conf(load_json(
                                    config.get('data', 'juniper_conf')))
            print 'juniper_conf consume done.'
        if config.get('data', 'nmap_services'):
            insert_nmap(load_json(config.get('data', 'nmap_services')))
            print 'nmap_services consume done.'
        if config.get('data', 'alcatel_isis'):
            consume_alcatel_isis(load_json(config.get('data', 'alcatel_isis')))
            print 'alcatel_isis consume done.'


    timestamp = datetime.datetime.strftime(datetime.datetime.now(),
        '%b %d %H:%M:%S')
    print '%s noclook_consumer.py ran successfully.' % timestamp
    return 0

if __name__ == '__main__':
    main()
