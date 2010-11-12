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
import ConfigParser
import argparse

## Need to change this path depending on where the Django project is
## located.
path = '/home/lundberg/norduni/scr/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from noclook.models import NodeType, NodeHandle
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

def insert_juniper(json_list):
    '''
    Inserts the data loaded from the json files created by juniper_conf.
    Some filtering is done for interface names that are not interesting.
    '''

    for i in json_list:
        name = i['host']['juniper_conf']['name']
        interfaces = i['host']['juniper_conf']['interfaces']

        nc = neo4jclient.Neo4jClient()

        # Hard coded values that we can't get on the fly right now
        user = User.objects.get(username="lundberg")
        type = NodeType.objects.get(slug="router")
        meta_type = 'physical'

        # Insert the router
        node_handle = NodeHandle(node_name=name, node_type=type,
            node_meta_type = meta_type, creator=user)
        node_handle.save()

        master_node = nc.get_node_by_id(node_handle.node_id)

        # Insert the interfaces
        not_interesting_interfaces = ['all', 'lo0', 'fxp0', '']
        for i in interfaces:
            name = i['name']
            if name not in not_interesting_interfaces:
                # Also not interesting is interfaces with . or * in them
                if '.' not in name and '*' not in name:
                    type = NodeType.objects.get(slug="pic")
                    node_handle = NodeHandle(node_name=name, node_type=type,
                        node_meta_type = meta_type, creator=user)
                    node_handle.save()
                    node = nc.get_node_by_id(node_handle.node_id)
                    node['description'] = i['desc']
                    node['units'] = json.dumps(i['units'])
                    master_node.Has(node)

def insert_nmap(json_list):
    '''
    Inserts the data loaded from the json files created by
    nmap_services.
    '''
    nc = neo4jclient.Neo4jClient()

    # Hard coded values that we can't get on the fly right now
    user = User.objects.get(username="lundberg")
    type = NodeType.objects.get(slug="host")
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
        node_handle = NodeHandle(node_name=name, node_type=type,
            node_meta_type = meta_type, creator=user)
        node_handle.save()

        # Set Node attributes
        node = nc.get_node_by_id(node_handle.node_id)
        node['hostnames'] = hostnames
        node['addresses'] = addresses
        node['services'] = services

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
        purge_db()

    # Insert data from known data sources if option -I was used
    if args.I:
        if config.get('data', 'juniper_conf') != '':
            insert_juniper(load_json(config.get('data', 'juniper_conf')))
        if config.get('data', 'nmap_services') != '':
            insert_nmap(load_json(config.get('data', 'nmap_services')))

    timestamp = datetime.datetime.strftime(datetime.datetime.now(),
        '%b %d %H:%M:%S')
    print "%s noclook_consumer.py ran successfully." % timestamp
    return 0

if __name__ == '__main__':
    main()
