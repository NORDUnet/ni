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

## Need to change this path depending on where the Django project is
## located.
#path = '/var/norduni/src/niweb/'
#path = '/home/jbn/stuff/work/code/norduni/src/niweb/'
path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.conf import settings as django_settings
from django.core.exceptions import ObjectDoesNotExist
from apps.noclook.models import NodeType, NodeHandle
from django.contrib.comments import Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
import norduni_client as nc
import noclook_juniper_consumer
import noclook_nmap_consumer
import noclook_alcatel_consumer

'''
This script is used for adding the objects collected with the
NERDS producers to the noclook database viewer.
'''

# SEARCH_INDEX_KEYS are only used when restoring backup nodes.
SEARCH_INDEX_KEYS = ['name', 'description', 'ip_address', 'ip_addresses',
                     'as_number', 'hostname']

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

def normalize_whitespace(text):
    '''
    Remove redundant whitespace from a string.
    '''
    text = text.replace('"', '').replace("'", '')
    return ' '.join(text.split())
        
def load_json(json_dir):
    '''
    Thinks all files in the supplied dir are text files containing json.
    '''
    json_list = []
    try:
        for subdir, dirs, files in os.walk(json_dir):
            for file in files:
                f=open(join(json_dir, file), 'r')
                json_list.append(json.load(f))
    except IOError as e:
        print 'Encountered a problem with %s.' % json_dir 
        print e
    return json_list

def generate_password(n):
    '''
    Returns a psudo random string of lenght n.
    http://code.activestate.com/recipes/576722-pseudo-random-string/
    '''
    import os, math
    from base64 import b64encode
    return b64encode(os.urandom(int(math.ceil(0.75*n))),'-_')[:n]

def get_user(username='noclook'):
    '''
    Gets or creates a user that can be used to insert data.
    '''
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        passwd = generate_password(30)
        user = User.objects.create_user(username, '', passwd)
    return user

def get_node_type(type_name):
    '''
    Returns or creates and returns the NodeType object with the supplied
    name.
    '''
    try:
        node_type = NodeType.objects.get(type=type_name)
    except NodeType.DoesNotExist:
        # The NodeType was not found, create one
        from django.template.defaultfilters import slugify
        node_type = NodeType(type=type_name, slug=slugify(type_name))
        node_type.save()
    return node_type

def get_unique_node_handle(db, node_name, node_type_name, node_meta_type):
    '''
    Takes the arguments needed to create a NodeHandle, if there already
    is a NodeHandle with the same name and type it will be considered
    the same one.
    Returns a NodeHandle object.
    '''
    user = get_user()
    node_type = get_node_type(node_type_name)
    try:
        node_handle = NodeHandle.objects.get(node_name=node_name,
                                            node_type=node_type)
    except NodeHandle.DoesNotExist:
        # The NodeHandle was not found, create one
        node_handle = NodeHandle.objects.create(node_name=node_name,
                                                node_type=node_type,
                                                node_meta_type=node_meta_type,
                                                creator=user,
                                                modifier=user)
        node_handle.save()
    return node_handle

def get_node_handle(db, node_name, node_type_name, node_meta_type,
                                                        parent=None):
    '''
    Takes the arguments needed to create a NodeHandle. If a parent is
    supplied the NodeHandle will be unique for that parent.
    Returns a NodeHandle object.
    *** This function does not handle multiple parents. ***
    '''
    user = get_user()
    node_type = get_node_type(node_type_name)
    try:
        if parent:
            node_handles = NodeHandle.objects.filter(node_name__in=[node_name]
                                            ).filter(node_type__in=[node_type])
            for node_handle in node_handles:
                node = node_handle.get_node()
                node_parent = nc.get_root_parent(db, node)
                if node_parent and parent.id == node_parent.id:
                    return node_handle # NodeHandle for that parent was found
    except ObjectDoesNotExist:
        # A NodeHandle was not found, create one
        pass
    node_handle = NodeHandle.objects.create(node_name=node_name,
                                            node_type=node_type,
                                            node_meta_type=node_meta_type,
                                            creator=user,
                                            modifier=user)
    node_handle.save()
    return node_handle # No NodeHandle found return a new handle.

def restore_node(db, handle_id, node_name, node_type_name, node_meta_type):
    '''
    Tries to get a existing node handle from the SQL database before creating
    a new handle with an old handle id.
    
    When we are setting the handle_id explicitly we need to run django-admin.py
    sqlsequencereset noclook and paste that SQL statements in to the dbhell.
    '''
    user = get_user()
    node_type = get_node_type(node_type_name)
    try:
        node_handle = NodeHandle.objects.get(handle_id=handle_id)
        node_handle.save(create_node=True)
    except ObjectDoesNotExist:
        # A NodeHandle was not found, create one
        node_handle = NodeHandle.objects.create(handle_id=handle_id, 
                                                node_name=node_name,
                                                node_type=node_type,
                                                node_meta_type=node_meta_type,
                                                creator=user,
                                                modifier=user)
        node_handle.save()
    return node_handle
    
def add_node_to_indexes(node, keys):
    '''
    If the node has any property keys matching the SEARCH_INDEX_KEYS the node
    will be added to the index with those values. The node will also be added
    to the node_types index.
    '''
    # Add the node_type to the node_types index.
    type_index = nc.get_node_index(nc.neo4jdb, 'node_types')
    nc.add_index_item(nc.neo4jdb, type_index, node, 'node_type')
    # Add the nodes to the search indexe
    search_index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
    for key in keys:
        nc.add_index_item(nc.neo4jdb, search_index, node, key)
    return node
    
def add_relationship_to_indexes(rel, keys):
    '''
    If the relationship has any property keys matching the SEARCH_INDEX_KEYS the 
    relationship will be added to the index with those values.
    '''
    # Add the nodes to the search indexe
    search_index = nc.get_relationship_index(nc.neo4jdb, nc.search_index_name())
    for key in keys:
        nc.add_index_item(nc.neo4jdb, search_index, rel, key)
    return rel

def set_comment(node_handle, comment):
    '''
    Sets the comment string as a comment for the provided node_handle.
    '''
    content_type = ContentType.objects.get_for_model(NodeHandle)
    object_pk = node_handle.pk
    user = get_user()
    site_id = django_settings.SITE_ID
    c = Comment(content_type = content_type, object_pk = object_pk, user = user,
                            site_id = site_id, comment = comment)
    c.save()

def consume_noclook(json_list):
    '''
    Inserts the backup made with NOCLook producer.
    '''
    # Remove all old node ids.
    NodeHandle.objects.all().update(node_id=None)
    # Loop through all files starting with node
    for i in json_list:
        if i['host']['name'].startswith('node'):
            item = i['host']['noclook_producer']
            properties = item.get('properties')
            node_name = properties.get('name')
            handle_id = properties.get('handle_id')
            node_type = properties.get('node_type')
            meta_type = item.get('meta_type')
            # Get a node handle
            nh = restore_node(nc.neo4jdb, handle_id, node_name, node_type, 
                                 meta_type) 
            node = nh.get_node()
            with nc.neo4jdb.transaction:
                node['old_node_id'] = item.get('id')
                node['handle_id'] = int(nh.handle_id)
            # Add all properties except the old NodeHandle id
            nc.update_item_properties(nc.neo4jdb, node, properties)
            # Add the old node id to an index for fast relationship adding
            index = nc.get_node_index(nc.neo4jdb, 'old_node_ids')
            nc.add_index_item(nc.neo4jdb, index, node, 'old_node_id')
            # Add the node to other indexes needed for NOCLook
            add_node_to_indexes(node, SEARCH_INDEX_KEYS)
            try:
                print 'Added node %d: %s %s %s. Handle ID: %d' % (node.id,
                    node['name'], node['node_type'], meta_type, nh.handle_id)
            except KeyError as e:
                print e
                print 'Handle ID: %d, node ID: %d' % (nh.handle_id, node.id)
                sys.exit(1)
    # Loop through all files starting with relationship
    for i in json_list:
        if i['host']['name'].startswith('relationship'):
            item = i['host']['noclook_producer']
            properties = item.get('properties')
            #start_node = nc.get_node_by_value(nc.neo4jdb, item.get('start'), 'old_node_id')
            start_node = nc.iter2list(index['old_node_id'][item['start']])
            end_node = nc.iter2list(index['old_node_id'][item['end']])
            #end_node = nc.get_node_by_value(nc.neo4jdb, item.get('end'), 'old_node_id')
            with nc.neo4jdb.transaction:
                rel = start_node[0].relationships.create(item.get('type'), 
                                                                    end_node[0])
            try:
                print start_node[0]['name'], item.get('type'), end_node[0]['name']
            except KeyError as e:
                print e
                print i
                sys.exit(1)
            nc.update_item_properties(nc.neo4jdb, rel, properties)
            # Add the relationship to indexes needed for NOCLook
            add_relationship_to_indexes(rel, SEARCH_INDEX_KEYS)
    # Remove the 'old_node_id' property from all nodes
    for n in nc.get_all_nodes(nc.neo4jdb):
        if n.getProperty('old_node_id', None):
            with nc.neo4jdb.transaction:
                del n['old_node_id']
    # Remove the temporary old_node_id index.
    with nc.neo4jdb.transaction:
        index = nc.get_node_index(nc.neo4jdb, 'old_node_ids')
        index.delete()

def run_consume(config_file):
    '''
    Function to start the consumer from another script.
    '''
    config = init_config(config_file)
    juniper_conf_data = config.get('data', 'juniper_conf')
    nmap_services_data = config.get('data', 'nmap_services')
    alcatel_isis_data = config.get('data', 'alcatel_isis')
    noclook_data = config.get('data', 'noclook')
    if juniper_conf_data:
        data = load_json(juniper_conf_data)
        noclook_juniper_consumer.consume_juniper_conf(data)
    if nmap_services_data:
        data = load_json(nmap_services_data)
        noclook_nmap_consumer.insert_nmap(data)
    if alcatel_isis_data:
        data = load_json(alcatel_isis_data)
        noclook_alcatel_consumer.consume_alcatel_isis(data)
    if noclook_data:
        data = load_json(noclook_data)
        consume_noclook(data)

def test_db():
    handles = NodeHandle.objects.all()
    print 'Handle\tNode'
    for handle in handles:
        print '%d\t%s' % (handle.handle_id, nc.get_node_by_id(
            handle.node_id))

def purge_db():
    for nh in NodeHandle.objects.all():
        nh.delete()

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
    # Start time
    start = datetime.datetime.now()
    timestamp_start = datetime.datetime.strftime(start,
        '%b %d %H:%M:%S')
    print '%s noclook_consumer.py was started.' % timestamp_start
    # Test DB connection
    if args.T:
        test_db()
    # Load the configuration file
    if not args.C:
        print 'Please provide a configuration file with -C.'
        sys.exit(1)
    # Purge DB if option -P was used
    if args.P:
        print 'Purging database...'
        purge_db()
    # Insert data from known data sources if option -I was used
    if args.I:
        print 'Inserting data...'
        run_consume(args.C)
    # end time
    end = datetime.datetime.now()
    timestamp_end = datetime.datetime.strftime(end,
        '%b %d %H:%M:%S')
    print '%s noclook_consumer.py ran successfully.' % timestamp_end
    timedelta = end - start
    print 'Total time: %s' % (timedelta)
    return 0

if __name__ == '__main__':
    main()
