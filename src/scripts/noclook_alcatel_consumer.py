#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       noclook_alcatel_consumer.py
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
import argparse

## Need to change this path depending on where the Django project is
## located.
#path = '/var/norduni/src/niweb/'
path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import noclook_consumer as nt
from apps.noclook import helpers as h
import norduni_client as nc

# This script is used for adding the objects collected with the
# NERDS producers alcatel_isis to the NOCLook database viewer.

# JSON format used:
# [{"host": {
#     "alcatel_isis": {
#         "data": {
#             "ip_address": "",
#             "link": "",
#             "name": "",
#             "osi_address": "",
#             "ots": "",
#             "type": ""
#         },
#         "name": "",
#         "neighbours": [
#             {
#                 "metric": "",
#                 "name": ""
#             },
#         ]
#     },
#     "name": "",
#     "version": 1
#     }
# }]

# The data block can hold any keys and don't necessarily have to be the ones
# listed above.

def consume_alcatel_isis(json_list):
    """
    Inserts the data loaded from the json files created by the nerds
    producer alcatel_isis.
    
    Metric = 0      "localhost"
    Metric = 12     "LAN connected"
    Metric = 19     "OMS - optical multiplex section connection"
                    (between LM's only)
    Metric = 20/21  "direct fiber connection"
    """
    # Insert the optical node
    for i in json_list:
        name = i['host']['alcatel_isis']['name']
        node_handle = nt.get_unique_node_handle(nc.neo4jdb, name, 
                                                'Optical Node', 'physical')
        node = node_handle.get_node()
        h.set_noclook_auto_manage(nc.neo4jdb, node, True)
        data = i['host']['alcatel_isis']['data']
        nc.update_item_properties(nc.neo4jdb, node, data)
        h.update_node_search_index(nc.neo4jdb, node)
        for neighbour in i['host']['alcatel_isis']['neighbours']:
            metric = neighbour['metric']
            if metric == '0':       # localhost
                break
            elif metric == '12':    # LAN connection (copper)
                cable_type = 'Patch'
            else:                   # Fiber
                cable_type = 'Dark Fiber'
            # Get or create a neighbour node
            neighbour_node_handle = nt.get_unique_node_handle(nc.neo4jdb, 
                                            neighbour['name'], 'Optical Node', 
                                            'physical')
            neighbour_node = neighbour_node_handle.get_node()
            h.update_noclook_auto_manage(nc.neo4jdb, neighbour_node)
            # See if the nodes already are connected via something
            create = True
            for rel in node.Connected_to.incoming:
                for rel2 in rel.start.Connected_to.outgoing:
                    if rel2.end['name'] == neighbour_node['name']:
                        create = False
                        h.update_noclook_auto_manage(nc.neo4jdb, rel.start)
                        break
            if create:
                cable_id = '%s - %s' % (node['name'], neighbour_node['name'])
                cable_node_handle = nt.get_unique_node_handle(nc.neo4jdb, 
                                                              cable_id, 
                                                              'Cable', 
                                                              'physical')
                cable_node = cable_node_handle.get_node()
                h.set_noclook_auto_manage(nc.neo4jdb, cable_node, True)
                with nc.neo4jdb.transaction:
                    cable_node['cable_type'] = cable_type
                h.update_node_search_index(nc.neo4jdb, cable_node)
                rels = nc.get_relationships(cable_node, node, 'Connected_to')
                if rels:
                    for rel in rels:
                        h.update_noclook_auto_manage(nc.neo4jdb, rel)
                else:
                    # Only create a relationship if it doesn't exist
                    rel = nc.create_relationship(nc.neo4jdb,
                                                          cable_node, node,
                                                          'Connected_to')
                    h.set_noclook_auto_manage(nc.neo4jdb, rel, True)
                rels = nc.get_relationships(cable_node, neighbour_node, 
                                                                'Connected_to')
                if rels:
                    for rel in rels:
                        h.update_noclook_auto_manage(nc.neo4jdb, rel)
                else:
                    # Only create a relationship if it doesn't exist
                    rel = nc.create_relationship(nc.neo4jdb,
                                                          cable_node, 
                                                          neighbour_node,
                                                          'Connected_to')
                    h.set_noclook_auto_manage(nc.neo4jdb, rel, True)

def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?',
        help='Path to the configuration file.')
    args = parser.parse_args()
    # Load the configuration file
    if not args.C:
        print 'Please provide a configuration file with -C.'
        sys.exit(1)
    else:
        config = nt.init_config(args.C)
        alcatel_isis_data = config.get('data', 'alcatel_isis')
    if alcatel_isis_data:
        consume_alcatel_isis(nt.load_json(alcatel_isis_data))
    return 0

if __name__ == '__main__':
    main()
