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

"""
Batch consumer script for the juniper_conf NERDS producer.

All graph-writing logic lives in apps.nerds.lib.juniper_consumer.
This script is a thin CLI wrapper: load JSON files from disk and hand
them to consume_juniper_conf().
"""

import sys
import argparse
import logging
import django_hack

import norduni.graphdb as nc
from . import utils
from norduni.apps.noclook import helpers
from norduni.apps.nerds.lib.juniper_consumer import consume_juniper_conf

django_hack.nop()

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
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?', help='Path to the configuration file.')
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    parser.add_argument('--switches', '-S', action='store_true', default=False, help='Insert as switches rather than routers')
    parser.add_argument('--data', '-d', required=False, help='Directory to load data from. Trumps config file.')
    args = parser.parse_args()
    if not args.C and not args.data:
        print('Please provide a configuration file with -C or --data for a data directory.')
        sys.exit(1)
    config = utils.init_config(args.C) if not args.data else None
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
