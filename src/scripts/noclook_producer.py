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

## Need to change this path depending on where the Django project is
## located.
base_path = '../niweb/'
sys.path.append(os.path.abspath(base_path))
niweb_path = os.path.join(base_path, 'niweb')
sys.path.append(os.path.abspath(niweb_path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.core.exceptions import ObjectDoesNotExist
from apps.noclook.models import NodeType
import norduniclient as nc

# A NERDS producer for the NOCLook application. It should be used to take
# backups of the data inserted manually in to the databases.

LABEL_NODE_TYPE_MAP = {}


def output(out_dir, json_list):
    # Pad with / if user provides a broken path
    if out_dir[-1] != '/':
        out_dir += '/'
    try:
        for host in json_list:
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


def labels_to_node_type(labels):
    for label in labels:
        node_type = LABEL_NODE_TYPE_MAP.get(label, None)
        if node_type:
            return node_type
        try:
            nt = NodeType.objects.get(type=label.replace('_', ' '))
            node_type = nt.type
            LABEL_NODE_TYPE_MAP[label] = node_type
            return node_type
        except ObjectDoesNotExist:
            pass


def labels_to_meta_type(labels):
    for label in labels:
        if label in nc.META_TYPES:
            return label


def nodes_to_json():
    json_list = []
    q = """
        MATCH (n:Node)
        RETURN labels(n),n
        """
    with nc.neo4jdb.read as r:
        for node in r.execute(q):
            labels, data = node
            json_list.append(
                {'host': {
                    'name': 'node_%d' % data['handle_id'],
                    'version': 1,
                    'noclook_producer': {
                        'handle_id': data['handle_id'],
                        'meta_type': labels_to_meta_type(labels),
                        'node_type': labels_to_node_type(labels),
                        'labels': labels,
                        'properties': data
                    }
                }})
    return json_list


def relationships_to_json():
    json_list = []
    q = """
        START r=relationship(*)
        RETURN  type(r), id(r), r, startNode(r).handle_id, endNode(r).handle_id
        """

    with nc.neo4jdb.read as r:
        for relationship in r.execute(q):
            t, i, data, start, end = relationship
            json_list.append(
                {'host': {
                    'name': 'relationship_%d' % i,
                    'version': 1,
                    'noclook_producer': {
                        'id': i,
                        'type': t,
                        'start': start,
                        'end': end,
                        'properties': data
                    }
                }})
    return json_list


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-O', nargs='?', help='Path to output directory.')
    parser.add_argument('-N', action='store_true', help='Don\'t write output to disk (JSON format).')
    args = parser.parse_args()

    # Create the json representation of nodes and relationships
    out_data = nodes_to_json()
    out_data.extend(relationships_to_json())

    if args.N:
        print json.dumps(out_data, sort_keys=True, indent=4)
    else:
        # Output directory should be ./json/ if nothing else is
        # specified
        out_dir = './json/'
        if args.O:
            out_dir = args.O
        output(out_dir, out_data)
    return 0

if __name__ == '__main__':
    main()

