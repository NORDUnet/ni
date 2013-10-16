#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       noclook_producer.py
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
import json
import argparse
import jpype
## Need to change this path depending on where the Django project is
## located.
path = '/home/lundberg/norduni/src/niweb/'
#path = '/var/norduni/scr/niweb/'
#path = '/var/opt/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import norduni_client as nc

# A NERDS producer for the NOCLook application. It should be used to take
# backups of the data inserted manually in to the databases.

#


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-O', nargs='?', help='Path to output directory.')
    parser.add_argument('-N', action='store_true', help='Don\'t write output to disk (JSON format).')
    args = parser.parse_args()
    
    # Node and relationships collections
    nodes = nc.get_all_nodes(nc.neo4jdb)
    rels = nc.get_all_relationships(nc.neo4jdb)

    # Create the json output
    out = []
    for node in nodes:
        # Disregard node 0 and the meta nodes
        if node.id and node['node_type'] != 'meta':
            meta_type = nc.get_node_meta_type(node)
            # Put the nodes json into the nerds format
            properties = {}
            for key in node.getPropertyKeys():
                properties[key] = node.get_property(key)
            out.append(
                {'host': {
                    'name': 'node_%d' % node.id,
                    'version': 1,
                    'noclook_producer': {
                        'id': node.id,
                        'meta_type': meta_type,
                        'properties': properties
                    }
                }})
                    
    for rel in rels:
        # Disregard the relationships connecting to node 0 or the meta nodes
        if rel.start.id and rel.start['node_type'] != 'meta':
            properties = {}
            for key in rel.getPropertyKeys():
                properties[key] = rel.get_property(key)
            out.append({'host':
                        {'name': 'relationship_%d' % rel.id,
                        'version': 1,
                        'noclook_producer': {'id': rel.id,
                                             'type': str(rel.type),
                                             'start': rel.start.id,
                                             'end': rel.end.id,
                                             'properties': properties}
                        }})

    if args.N:
        print json.dumps(out, sort_keys=True, indent=4)
    else:
        # Output directory should be ./json/ if nothing else is
        # specified
        out_dir = './json/'
        if args.O:
            out_dir = args.O
        # Pad with / if user provides a broken path
        if out_dir[-1] != '/':
            out_dir += '/'
        try:
            for host in out:
                hostn = host['host']['name']
                try:
                    f = open('%s%s.json' % (out_dir, hostn), 'w')
                except IOError as (errno, strerror):
                    print "I/O error({0}): {1}".format(errno, strerror)
                    # The directory to write in must exist
                    os.mkdir(out_dir)
                    f = open('%s%s.json' % (out_dir, hostn), 'w')
                f.write(json.dumps(host, sort_keys=True, indent=4))
                f.close()
        except IOError as (errno, strerror):
            print 'When trying to open output file.'
            print "I/O error({0}): {1}".format(errno, strerror)

    return 0

if __name__ == '__main__':
    main()

