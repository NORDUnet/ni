# -*- coding: utf-8 -*-
__author__ = 'lundberg'

import sys
import os
import argparse
from datetime import datetime
import ConfigParser
import json


base_path = '/home/lundberg/projects/norduni2.0/src/niweb/'
sys.path.append(os.path.abspath(base_path))
niweb_path = os.path.join(base_path, 'niweb')
sys.path.append(os.path.abspath(niweb_path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.conf import settings as django_settings
from apps.noclook.models import NodeType, NodeHandle
from apps.noclook import helpers as h
from apps.noclook import activitylog
import norduniclient as nc


def init_config(path):
    """
    Initializes the configuration file located in the path provided.
    """
    try:
        config = ConfigParser.SafeConfigParser()
        config.read(path)
        return config
    except IOError as (errno, strerror):
        print "I/O error({0}): {1}".format(errno, strerror)


def load_json(json_dir):
    """
    Thinks all files in the supplied dir are text files containing json.
    """
    json_list = []
    try:
        for subdir, dirs, files in os.walk(json_dir):
            for a_file in files:
                try:
                    f = open(os.path.join(json_dir, a_file), 'r')
                    json_list.append(json.load(f))
                except ValueError as e:
                    print 'Encountered a problem with %s.' % a_file
                    print e
    except IOError as e:
        print 'Encountered a problem with %s.' % json_dir
        print e
    return json_list


def get_user(username='noclook'):
    """
    Gets or creates a user that can be used to insert data.
    """

    def generate_password(n):
        """
        Returns a psudo random string of lenght n.
        http://code.activestate.com/recipes/576722-pseudo-random-string/
        """
        import os, math
        from base64 import b64encode

        return b64encode(os.urandom(int(math.ceil(0.75 * n))), '-_')[:n]

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        passwd = generate_password(30)
        user = User.objects.create_user(username, '', passwd)
    return user


def get_node_type(type_name):
    """
    Returns or creates and returns the NodeType object with the supplied
    name.
    """
    try:
        node_type = NodeType.objects.get(type=type_name)
    except NodeType.DoesNotExist:
        # The NodeType was not found, create one
        from django.template.defaultfilters import slugify
        node_type = NodeType(type=type_name, slug=slugify(type_name))
        node_type.save()
    return node_type


def restore_node(handle_id, node_name, node_type_name, node_meta_type):
    """
    Tries to get a existing node handle from the SQL database before creating
    a new handle with an old handle id.

    When we are setting the handle_id explicitly we need to run django-admin.py
    sqlsequencereset noclook and paste that SQL statements in to the dbhell.
    """
    user = get_user()
    node_type = get_node_type(node_type_name)
    defaults = {
        'node_name': node_name,
        'node_type': node_type,
        'node_meta_type': node_meta_type,
        'creator': user,
        'modifier': user
    }
    node_handle, created = NodeHandle.objects.get_or_create(handle_id=handle_id, defaults=defaults)
    if not created:
        node_handle.node_meta_type = node_meta_type
    node_handle.save()  # Create a node
    return node_handle


def insert_graph_data(json_list):

    with nc.neo4jdb.transaction as w:
        w.execute('CREATE CONSTRAINT ON (n:Node) ASSERT n.old_node_id IS UNIQUE')

    # Loop through all files starting with node
    for i in json_list:
        if i['host']['name'].startswith('node'):
            item = i['host']['noclook_producer']
            properties = item.get('properties')
            node_name = properties.get('name')
            handle_id = properties.get('handle_id')
            node_type = properties.get('node_type')
            meta_type = item.get('meta_type').capitalize()  # Labels are nicer capitalized
            # Get a node handle
            nh = restore_node(handle_id, node_name, node_type, meta_type)
            # We need the old node id to create relationships, this will be removed later.
            properties['old_node_id'] = item.get('id')
            # Add all properties
            node = nc.update_node_properties(nc.neo4jdb, nh.handle_id, properties)
            try:
                print u'Added node {meta_type} {node_type} {name} with handle ID: {handle_id}'.format(
                      name=node['name'], node_type=node_type, meta_type=meta_type, handle_id=node['handle_id'])
            except KeyError as e:
                print e
                print 'Failed at handle ID: {handle_id}'.format(handle_id=nh.handle_id)
                sys.exit(1)

    # Loop through all files starting with relationship
    for i in json_list:
        if i['host']['name'].startswith('relationship'):
            item = i['host']['noclook_producer']
            properties = item.get('properties')

            props = {'props': properties}
            q = """
                MATCH (start:Node {old_node_id: {start_id}), (end:Node {old_node_id: {end_id})
                CREATE UNIQUE (start)-[r:%s { props } ]->(end)
                RETURN start.name, type(r), end.name
                """ % item.get('type')
            with nc.neo4jdb.write as w:
                start, rel_type, end = w.execute(
                    q, start_id=item.get('start'), end_id=item.get('end'), **props).fetchall()
                print '{start} -[{rel_type}]-> {end}'.format(start=start, rel_type=rel_type, end=end)

    # Remove the 'old_node_id' property from all nodes
    q = """
        MATCH (n:Node)
        REMOVE n.old_node_id
        """
    with nc.neo4jdb.write as w:
        w.execute(q)
        w.execute('DROP CONSTRAINT ON (n:Node) ASSERT n.old_node_id IS UNIQUE')


def run_consume(config_file):
    config = init_config(config_file)
    noclook_data = config.get('data', 'noclook')
    if noclook_data:
        data = load_json(noclook_data)
        insert_graph_data(data)


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?', help='Path to the configuration file.')
    parser.add_argument('-I', action='store_true', help='Insert data in to the database.')
    args = parser.parse_args()

    # Load the configuration file
    if not args.C:
        print 'Please provide a configuration file with -C.'
        sys.exit(1)

    # Start time
    start = datetime.now()
    timestamp_start = datetime.strftime(start, '%b %d %H:%M:%S')
    print '%s - NOClook upgrade started...' % timestamp_start

    # Insert data from known data sources if option -I was used
    if args.I:
        print 'Inserting data...'
        run_consume(args.C)

    # end time
    end = datetime.now()
    timestamp_end = datetime.strftime(end, '%b %d %H:%M:%S')
    print '%s NOClook upgrade ran successfully.' % timestamp_end
    timedelta = end - start
    print 'Total time: %s' % timedelta
    return 0

if __name__ == '__main__':
    main()