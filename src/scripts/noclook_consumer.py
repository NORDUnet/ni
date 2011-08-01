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

def rest_comp(data):
    '''
    As the REST interface cant handle None type change None to False.
    '''
    if data is None:
        return False
    return data
        
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

def test_db():
    handles = NodeHandle.objects.all()
    print 'Handle\tNode'
    for handle in handles:
        print '%d\t%s' % (handle.handle_id, nc.get_node_by_id(
            handle.node_id))

def purge_db():
#    for h in NodeHandle.objects.all():
#        try:
#            nc.delete_node(h.node_id)
#        except nc.client.NotFoundError:
#            print 'Could not delete the Neo4j node.' 
    NodeHandle.objects.all().delete()

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
    except Exception:
        # The NodeType was not found, create one
        from django.template.defaultfilters import slugify
        node_type = NodeType(type=type_name, slug=slugify(type_name))
        node_type.save()
    return node_type

def get_unique_node_handle(node_name, node_type_name, node_meta_type):
    '''
    Takes the arguments needed to create a NodeHandle, if there already
    is a NodeHandle with the same name and type it will be considered
    the same one.
    Returns a NodeHandle object.
    '''
    # Hard coded user value that we can't get on the fly right now
    user = get_user()
    node_type = get_node_type(node_type_name)
    try:
        node_handle = NodeHandle.objects.get(node_name=node_name,
                                            node_type=node_type)
    except Exception:
        # The NodeHandle was not found, create one
        node_handle = NodeHandle(node_name=node_name,
                                node_type=node_type,
                                node_meta_type=node_meta_type,
                                creator=user)
        node_handle.save()
    return node_handle

def get_node_handle(node_name, node_type_name, node_meta_type,
                                                        parent=None):
    '''
    Takes the arguments needed to create a NodeHandle. If a parent is
    supplied the NodeHandle will be unique for that parent.
    Returns a NodeHandle object.
    '''
    # Hard coded user value that we can't get on the fly right now
    user = get_user()
    node_type = get_node_type(node_type_name)
    try:
        node_handles = NodeHandle.objects.filter(
                                            node_name__in=[node_name]
                                            ).filter(
                                            node_type__in=[node_type])
        if parent:
            for node_handle in node_handles:
                node = node_handle.get_node()
                if parent.id == nc.get_root_parent(node, nc.Incoming.Has).id:
                    return node_handle # NodeHandle for that parent was found
    except ObjectDoesNotExist:
        # A NodeHandle was not found, create one
        pass
    node_handle = NodeHandle(node_name=node_name,
                            node_type=node_type,
                            node_meta_type=node_meta_type,
                            creator=user)
    node_handle.save()
    return node_handle # No NodeHandle found return a new handle.

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
    # Loop through all files starting with node
    for i in json_list:
        if i['host']['name'].startswith('node'):
            item = i['host']['noclook_producer']
            properties = item.get('properties')
            node_name = properties.get('name')
            node_type = properties.get('type')
            meta_type = item.get('meta_type')
            # Get a node handle
            nh = get_node_handle(node_name, node_type, meta_type) 
            node = nh.get_node()
            node['old_node_id'] = item.get('id')
            # Add all properties except the old NodeHandle id
            nc.update_node_properties(node.id, properties)
            node['handle_id'] = int(nh.handle_id)
    # Loop through all files starting with relationship
    for i in json_list:
        if i['host']['name'].startswith('relationship'):
            item = i['host']['noclook_producer']
            properties = item.get('properties')
            start_node = nc.get_node_by_value(node_value=item.get('start'),
                                              node_property='old_node_id')
            end_node = nc.get_node_by_value(node_value=item.get('end'),
                                              node_property='old_node_id')
            rel = start_node[0].relationships.create(item.get('type'), 
                                                                    end_node[0])
            nc.update_relationship_properties(start_node.id, rel.id, properties)
    # Remove the 'old_node_id' property from all nodes
    for n in nc.get_all_nodes():
        if 'old_node_id' in n:
            del n['old_node_id']

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
    else:
        config = init_config(args.C)
    # Purge DB if option -P was used
    if args.P:
        print 'Purging database...'
        purge_db()
    # Insert data from known data sources if option -I was used
    if args.I:
        print 'Loading data...'
        juniper_conf_data = config.get('data', 'juniper_conf')
        nmap_services_data = config.get('data', 'nmap_services')
        alcatel_isis_data = config.get('data', 'alcatel_isis')
        noclook_data = config.get('data', 'noclook')
        print 'Inserting data...'
        if juniper_conf_data:
            data = load_json(juniper_conf_data)
            noclook_juniper_consumer.consume_juniper_conf(data)
            print 'juniper_conf consume done.'
        if nmap_services_data:
            data = load_json(nmap_services_data)
            noclook_nmap_consumer.insert_nmap(data)
            print 'nmap_services consume done.'
        if alcatel_isis_data:
            data = load_json(alcatel_isis_data)
            noclook_alcatel_consumer.consume_alcatel_isis(data)
            print 'alcatel_isis consume done.'
        if noclook_data:
            data = load_json(noclook_data)
            consume_noclook(data)
            print 'noclook consume done.'
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
