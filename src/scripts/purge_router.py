# -*- coding: utf-8 -*-
#
#       purge_router.py
#
#       Copyright 2017 Markus Krogh <markus@nordu.net>
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
import argparse
import logging

## Need to change this path depending on where the Django project is
## located.
base_path = '../niweb/'
sys.path.append(os.path.abspath(base_path))
niweb_path = os.path.join(base_path, 'niweb')
sys.path.append(os.path.abspath(niweb_path))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "niweb.settings.prod")

import noclook_consumer as nt
from apps.noclook import helpers
from apps.noclook import activitylog
import norduniclient as nc
from dynamic_preferences import global_preferences_registry
from apps.noclook.models import UniqueIdGenerator

logger = logging.getLogger('noclook_purge_router')


delete_log = []

def delete_node(node, dry_run):
    if not dry_run:
        user = nt.get_user()
        helpers.delete_node(user, node.handle_id)
    logger.info('Deleted node {handle_id}.'.format(handle_id=node.handle_id))
    delete_log.append(node.handle_id)


def remove_router_conf(router_name, data_age, dry_run=False):
    routerq = """
        MATCH (router:Node:Router {{name: '{}'}})
        OPTIONAL MATCH (router)-[:Has*1..]->(physical)
        OPTIONAL MATCH (physical)<-[:Part_of]-(logical)
        WHERE (physical.noclook_auto_manage = true) OR (logical.noclook_auto_manage = true)
        RETURN collect(distinct physical.handle_id) as physical, collect(distinct logical.handle_id) as logical
        """.format(router_name)
    router_result = nc.query_to_dict(nc.neo4jdb, routerq)
    for handle_id in router_result.get('logical', []):
        logical = nc.get_node_model(nc.neo4jdb, handle_id)
        if logical:
            last_seen, expired = helpers.neo4j_data_age(logical.data, data_age)
            if expired:
                delete_node(logical, dry_run)
    for handle_id in router_result.get('physical', []):
        physical = nc.get_node_model(nc.neo4jdb, handle_id)
        if physical:
            last_seen, expired = helpers.neo4j_data_age(physical.data, data_age)
            if expired:
                delete_node(physical, dry_run)


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('router_name', help='Name of the router to purge.')
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    parser.add_argument('--dry-run', '-N', action='store_true', default=False)
    parser.add_argument('--age', '-a', default='24', help='How old in hours should a port or unit be before purging.')
    args = parser.parse_args()
    # Load the configuration file
    if args.verbose:
        logger.setLevel(logging.INFO)
    remove_router_conf(args.router_name, args.age, args.dry_run)
    logger.info("Nodes deleted: {}".format(delete_log))
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
