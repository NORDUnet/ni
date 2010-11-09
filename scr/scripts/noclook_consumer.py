#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       juniper_add.py
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
sys.path.append(os.path.abspath('/home/lundberg/norduni/scr/niweb'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from noclook.models import NodeType, NodeHandle
from django.contrib.auth.models import User
import neo4jclient
from os.path import join
import json

'''
This script is used for adding the objects collected with the
NERDS juniper_conf producer to the noclook database viewer.
'''

def test_setup():
    handles = NodeHandle.objects.all()
    print 'Handle\tNode'
    for handle in handles:
        print '%d\t%d' % (handle.handle_id, handle.node_id)

def purge_db():
    nc = neo4jclient.Neo4jClient()
    for h in NodeHandle.objects.all():
        nc.delete_node(h.node_id)
    NodeHandle.objects.all().delete()

def insert_physical(name, interfaces):
    '''
    Inserts the data loaded from the json files in to the databases.
    Some filtering is done for interface names that are not interesting.
    '''
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
                node['number_of_units'] = len(i['units'])
                master_node.Has(node)

def main():

    # Insert for insert and purge to remove all handles and nodes.
    #insert = False
    purge = True
    insert = True
   # purge = False

    json_dir = '/home/lundberg/norduni/tools/nerds/producers/juniper_conf/json/'
    json_list = []

    for subdir, dirs, files in os.walk(json_dir):
        for file in files:
            f=open(join(json_dir, file), 'r')
            json_list.append(json.load(f))

    if purge:
        purge_db()

    if insert:
        for i in json_list:
            name = i['host']['juniper_conf']['name']
            interfaces = i['host']['juniper_conf']['interfaces']
            insert_physical(name, interfaces)

    return 0

if __name__ == '__main__':
    main()
