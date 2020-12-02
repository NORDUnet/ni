#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       sri_restore.py
#
#       Copyright 2020 Johan Lundberg <lundberg@sunet.se>
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
import datetime
import argparse
import logging
import utils

from apps.noclook.models import NodeHandle, NodeHandleContext
import apps.noclook.vakt.utils as sriutils
from django.conf import settings as django_settings
from django_comments.models import Comment
from django.contrib.contenttypes.models import ContentType
import norduniclient as nc

logger = logging.getLogger('sri_restore')
# This script is used for restoring NI data to an SRI instance

NODE_HANDLE_ID_MAPPING = {}


def normalize_whitespace(text):
    """
    Remove redundant whitespace from a string.
    """
    text = text.replace('"', '').replace("'", '')
    return ' '.join(text.split())


def generate_password(n):
    import random

    return ''.join(
        [random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789@#$%^&*(-_=+)') for i in range(n)]
    )


def get_unique_node(name, node_type, meta_type):
    """
    Gets or creates a NodeHandle with the provided name.
    Returns the NodeHandles node.
    """
    name = normalize_whitespace(name)
    node_handle = utils.get_unique_node_handle(name, node_type, meta_type)
    node = node_handle.get_node()
    return node


def restore_node(handle_id, node_name, node_type_name, node_meta_type, fallback_user):
    """
    Tries to get a existing node handle from the SQL database before creating
    a new handle with an old handle id. If an existing node if found do not overwrite it.

    When we are setting the handle_id explicitly we need to run django-admin.py
    sqlsequencereset noclook and paste that SQL statements in to the dbhell.
    """
    node_type = utils.get_node_type(node_type_name)
    defaults = {
        'node_name': node_name,
        'node_type': node_type,
        'node_meta_type': node_meta_type,
        'creator': fallback_user,
        'modifier': fallback_user,
    }
    if NodeHandle.objects.filter(handle_id=handle_id).exists():
        # NodeHandle id already taken, create a new NodeHandle and map old id to new
        node_handle = NodeHandle.objects.create(**defaults)
        created = True
        NODE_HANDLE_ID_MAPPING[handle_id] = node_handle.handle_id
        logger.info('Remapping handle_id {} to {}'.format(handle_id, node_handle.handle_id))
    else:
        node_handle, created = NodeHandle.objects.get_or_create(handle_id=handle_id, defaults=defaults)
    if not created:
        if node_handle.node_meta_type != node_meta_type:
            node_handle.node_meta_type = node_meta_type
            node_handle.save()
    # rather than calling .save() which will do a db fetch of node_type
    node_handle._create_node(node_type.get_label())  # Make sure data is saved in neo4j as well.

    # Create NodeHandleContext
    net_ctx = sriutils.get_network_context()
    NodeHandleContext.objects.get_or_create(nodehandle=node_handle, context=net_ctx)

    return node_handle


def set_comment(node_handle, comment):
    """
    Sets the comment string as a comment for the provided node_handle.
    """
    content_type = ContentType.objects.get_for_model(NodeHandle)
    object_pk = node_handle.pk
    user = utils.get_user()
    site_id = django_settings.SITE_ID
    c = Comment(content_type=content_type, object_pk=object_pk, user=user, site_id=site_id, comment=comment)
    c.save()


def _consume_node(item, fallback_user):
    properties = item.get('properties')
    node_name = properties.get('name')
    handle_id = item.get('handle_id')
    node_type = item.get('node_type')
    meta_type = item.get('meta_type')
    try:
        # Get a node handle
        nh = restore_node(handle_id, node_name, node_type, meta_type, fallback_user)
        nc.set_node_properties(nc.graphdb.manager, nh.handle_id, properties)
        logger.info('Added node {handle_id}.'.format(handle_id=handle_id))
    except Exception as e:
        import traceback

        traceback.print_exc()
        ex_type = type(e).__name__
        logger.error(
            'Could not add node {} (handle_id={}, node_type={}, meta_type={}) got {}: {})'.format(
                node_name, handle_id, node_type, meta_type, ex_type, str(e)
            )
        )


def consume_noclook(nodes, relationships):
    """
    Inserts the backup made with NOCLook producer.
    """
    tot_nodes = 0
    tot_rels = 0
    fallback_user = utils.get_user()
    # Loop through all files starting with node
    for i in nodes:
        item = i['host']['noclook_producer']
        if i['host']['name'].startswith('node'):
            _consume_node(item, fallback_user)
            tot_nodes += 1
    print('Added {!s} nodes.'.format(tot_nodes))

    # Loop through all files starting with relationship
    for i in relationships:
        rel = i['host']['noclook_producer']
        start_id = rel.get('start')
        end_id = rel.get('end')
        properties = rel.get('properties')

        # Check for handle_id remapping
        if start_id in NODE_HANDLE_ID_MAPPING:
            start_id = NODE_HANDLE_ID_MAPPING[start_id]
        if end_id in NODE_HANDLE_ID_MAPPING:
            end_id = NODE_HANDLE_ID_MAPPING[end_id]

        q = """
             MATCH (start:Node { handle_id: {start_id} }),(end:Node {handle_id: {end_id} })
             CREATE UNIQUE (start)-[r:%s {props} ]->(end)
             """ % rel.get(
            'type'
        )
        query_data = {'props': properties, 'start_id': start_id, 'end_id': end_id}

        with nc.graphdb.manager.session as s:
            s.run(q, query_data)
        logger.info('{start}-[{rel_type}]->{end}'.format(start=start_id, rel_type=rel.get('type'), end=end_id))
        tot_rels += 1
    print('Added {!s} relationships.'.format(tot_rels))


def run_restore(config_file):
    """
    Function to start the consumer from another script.
    """
    config = utils.init_config(config_file)
    noclook_data = config.get('data', 'noclook')
    if noclook_data:
        nodes = utils.load_json(noclook_data, starts_with="node")
        relationships = utils.load_json(noclook_data, starts_with="relationship")
        consume_noclook(nodes, relationships)


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?', help='Path to the configuration file.')
    parser.add_argument('-I', action='store_true', help='Insert data in to the database.')
    parser.add_argument('-V', action='store_true', default=False)
    args = parser.parse_args()
    # Start time
    start = datetime.datetime.now()
    timestamp_start = datetime.datetime.strftime(start, '%b %d %H:%M:%S')
    print('%s sri_restore.py was started.' % timestamp_start)
    # Load the configuration file
    if not args.C:
        print('Please provide a configuration file with -C.')
        sys.exit(1)
    if args.V:
        logger.setLevel(logging.INFO)
    # Insert data from known data sources if option -I was used
    if args.I:
        print('Inserting data...')
        run_restore(args.C)
    # end time
    end = datetime.datetime.now()
    timestamp_end = datetime.datetime.strftime(end, '%b %d %H:%M:%S')
    print('%s sri_restore.py ran successfully.' % timestamp_end)
    timedelta = end - start
    print('Total time: %s' % timedelta)
    print('Now run "django-admin.py sqlsequencereset noclook" and paste that SQL statements in to the dbhell')
    return 0


if __name__ == '__main__':
    logger.propagate = False
    logger.setLevel(logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    main()
