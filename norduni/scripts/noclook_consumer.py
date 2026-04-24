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
import random
import datetime
import argparse
import logging
import traceback
from collections import defaultdict
from . import utils

from norduni.apps.noclook.models import NodeHandle
from django.conf import settings as django_settings
from django_comments.models import Comment
from django.contrib.contenttypes.models import ContentType
import norduni.graphdb as nc

from . import noclook_juniper_consumer
from . import noclook_nmap_consumer
from . import noclook_checkmk_consumer
from . import noclook_cfengine_consumer
from . import noclook_nunoc_consumer

logger = logging.getLogger('noclook_consumer')
# This script is used for adding the objects collected with the
# NERDS producers to the NOCLook database viewer.


def normalize_whitespace(text):
    """
    Remove redundant whitespace from a string.
    """
    text = text.replace('"', '').replace("'", '')
    return ' '.join(text.split())


def generate_password(n):
    return ''.join([random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789@#$%^&*(-_=+)') for i in range(n)])


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
    a new handle with an old handle id.

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
    node_handle, created = NodeHandle.objects.get_or_create(handle_id=handle_id, defaults=defaults)
    if not created:
        if node_handle.node_meta_type != node_meta_type:
            node_handle.node_meta_type = node_meta_type
            node_handle.save()
    # rather than calling .save() which will do a db fetch of node_type
    node_handle._create_node(node_type.get_label())  # Make sure data is saved in neo4j as well.
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
    try:
        properties = item.get('properties')
        node_name = properties.get('name')
        handle_id = item.get('handle_id')
        node_type = item.get('node_type')
        meta_type = item.get('meta_type')
        # Get a node handle
        nh = restore_node(handle_id, node_name, node_type, meta_type, fallback_user)
        nc.set_node_properties(nc.graphdb.manager, nh.handle_id, properties)
        logger.info('Added node {handle_id}.'.format(handle_id=handle_id))
    except Exception as e:
        traceback.print_exc()
        ex_type = type(e).__name__
        logger.error('Could not add node {} (handle_id={}, node_type={}, meta_type={}) got {}: {})'.format(node_name, handle_id, node_type, meta_type, ex_type, str(e)))


def consume_noclook(nodes, relationships):
    """
    Inserts the backup made with NOCLook producer.

    Batches all operations to minimise Neo4j session round-trips and use
    bulk SQL inserts for Django NodeHandles.
    """
    BATCH_SIZE = 500

    def _chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    fallback_user = utils.get_user()

    # Nodes
    node_items = [
        i['host']['noclook_producer']
        for i in nodes
        if i['host']['name'].startswith('node')
    ]

    # Cache NodeType lookups (one query per distinct type name instead of one per node)
    type_cache = {}
    for item in node_items:
        name = item.get('node_type')
        if name not in type_cache:
            type_cache[name] = utils.get_node_type(name)

    # Bulk-create Django NodeHandles (skips already-existing handles)
    # bulk_create does NOT call save() so we handle Neo4j separately below.
    handles = [
        NodeHandle(
            handle_id=item.get('handle_id'),
            node_name=item.get('properties', {}).get('name'),
            node_type=type_cache[item.get('node_type')],
            node_meta_type=item.get('meta_type'),
            creator=fallback_user,
            modifier=fallback_user,
        )
        for item in node_items
    ]
    NodeHandle.objects.bulk_create(handles, ignore_conflicts=True)

    # Update node_meta_type on any already-existing handles where it has changed
    meta_by_id = {h.handle_id: h.node_meta_type for h in handles}
    to_update = []
    for nh in NodeHandle.objects.filter(handle_id__in=meta_by_id):
        if nh.node_meta_type != meta_by_id[nh.handle_id]:
            nh.node_meta_type = meta_by_id[nh.handle_id]
            to_update.append(nh)
    if to_update:
        NodeHandle.objects.bulk_update(to_update, ['node_meta_type'])

    # Batch Neo4j node creation grouped by (meta_type, type_label).
    # Labels can't be parameterised in Cypher so we issue one UNWIND per group.
    neo4j_groups = defaultdict(list)
    for item in node_items:
        meta_type = item.get('meta_type')
        type_label = type_cache[item.get('node_type')].get_label()
        neo4j_groups[(meta_type, type_label)].append({
            'handle_id': item.get('handle_id'),
            'name': item.get('properties', {}).get('name'),
        })

    all_props = []
    for item in node_items:
        props = dict(item.get('properties') or {})
        props['handle_id'] = item.get('handle_id')
        all_props.append({'handle_id': item.get('handle_id'), 'props': props})

    for (meta_type, type_label), group in neo4j_groups.items():
        q = """
            UNWIND $nodes AS n
            MERGE (node:Node:%s:%s {handle_id: n.handle_id})
            ON CREATE SET node.name = n.name
            """ % (meta_type, type_label)
        for chunk in _chunks(group, BATCH_SIZE):
            with nc.graphdb.manager.session as s:
                s.run(q, {'nodes': chunk})

    set_q = """
        UNWIND $items AS item
        MATCH (n:Node {handle_id: item.handle_id})
        SET n = item.props
        """
    for chunk in _chunks(all_props, BATCH_SIZE):
        with nc.graphdb.manager.session as s:
            s.run(set_q, {'items': chunk})

    tot_nodes = len(node_items)
    print('Added {!s} nodes.'.format(tot_nodes))

    # Relationships
    # Group by (type, sorted property keys) to preserve the original MERGE
    # semantics where relationship identity included all properties.
    rel_groups = defaultdict(list)
    for i in relationships:
        rel = i['host']['noclook_producer']
        rel_type = rel.get('type')
        properties = rel.get('properties') or {}
        prop_keys = tuple(sorted(properties.keys()))
        rel_groups[(rel_type, prop_keys)].append({
            'start': rel.get('start'),
            'end': rel.get('end'),
            'props': properties,
        })

    for (rel_type, prop_keys), rels in rel_groups.items():
        if prop_keys:
            propmap = ', '.join(['{k}: r.props.{k}'.format(k=k) for k in prop_keys])
            q = """
                UNWIND $rels AS r
                MATCH (start:Node {handle_id: r.start}), (end:Node {handle_id: r.end})
                MERGE (start)-[rel:%s {%s}]->(end)
                """ % (rel_type, propmap)
        else:
            q = """
                UNWIND $rels AS r
                MATCH (start:Node {handle_id: r.start}), (end:Node {handle_id: r.end})
                MERGE (start)-[rel:%s]->(end)
                """ % rel_type
        for chunk in _chunks(rels, BATCH_SIZE):
            with nc.graphdb.manager.session as s:
                s.run(q, {'rels': chunk})

    tot_rels = sum(len(v) for v in rel_groups.values())
    print('Added {!s} relationships.'.format(tot_rels))


def run_consume(config_file):
    """
    Function to start the consumer from another script.
    """
    config = utils.init_config(config_file)
    # juniper_conf
    juniper_conf_data = config.get('data', 'juniper_conf')
    remove_expired_juniper_conf = config.getboolean('delete_data', 'juniper_conf')
    juniper_conf_data_age = config.get('data_age', 'juniper_conf')
    # nmap services
    nmap_services_py_data = config.get('data', 'nmap_services_py')
    # nagios checkmk
    nagios_checkmk_data = config.get('data', 'nagios_checkmk')
    # cfengine report
    cfengine_data = config.get('data', 'cfengine_report')
    # noclook
    noclook_data = config.get('data', 'noclook')
    # Consume data
    if juniper_conf_data:
        data = utils.load_json(juniper_conf_data)
        switches = False
        noclook_juniper_consumer.consume_juniper_conf(data, switches)
    if nmap_services_py_data:
        data = utils.load_json(nmap_services_py_data)
        noclook_nmap_consumer.insert_nmap(data)
    if nagios_checkmk_data:
        data = utils.load_json(nagios_checkmk_data)
        noclook_checkmk_consumer.insert(data)
    if cfengine_data:
        data = utils.load_json(cfengine_data)
        noclook_cfengine_consumer.insert(data)
    if config.has_option('data', 'nunoc_cosmos'):
        data = utils.load_json(config.get('data', 'nunoc_cosmos'))
        noclook_nunoc_consumer.insert_hosts(data)
    if noclook_data:
        nodes = utils.load_json(noclook_data, starts_with="node")
        relationships = utils.load_json(noclook_data, starts_with="relationship")
        consume_noclook(nodes, relationships)
    # Clean up expired data
    if remove_expired_juniper_conf:
        noclook_juniper_consumer.remove_juniper_conf(juniper_conf_data_age)


def purge_db():
    for nh in NodeHandle.objects.all():
        nh.delete()


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?', help='Path to the configuration file.')
    parser.add_argument('-P', action='store_true', help='Purge the database.')
    parser.add_argument('-I', action='store_true', help='Insert data in to the database.')
    parser.add_argument('-V', action='store_true', default=False)
    args = parser.parse_args()
    # Start time
    start = datetime.datetime.now()
    timestamp_start = datetime.datetime.strftime(start, '%b %d %H:%M:%S')
    print('%s noclook_consumer.py was started.' % timestamp_start)
    # Load the configuration file
    if not args.C:
        print('Please provide a configuration file with -C.')
        sys.exit(1)
    # Purge DB if option -P was used
    if args.P:
        print('Purging database...')
        purge_db()
    if args.V:
        logger.setLevel(logging.INFO)
    # Insert data from known data sources if option -I was used
    if args.I:
        print('Inserting data...')
        run_consume(args.C)
    # end time
    end = datetime.datetime.now()
    timestamp_end = datetime.datetime.strftime(end, '%b %d %H:%M:%S')
    print('%s noclook_consumer.py ran successfully.' % timestamp_end)
    timedelta = end - start
    print('Total time: %s' % timedelta)
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
