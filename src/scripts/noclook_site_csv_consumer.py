#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       noclook_consumer.py
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

import sys
import os
import datetime
import argparse

## Need to change this path depending on where the Django project is
## located.
path = '/var/norduni/src/niweb/'
#path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
import noclook_consumer as nt
import norduni_client as nc
from apps.noclook import helpers as h

'''
This script is used for adding the objects collected with the
NERDS csv producer from the NORDUnet site spreadsheets.

{
    "host": {
        "csv_producer": {
            "address": "", 
            "area": "", 
            "city": "", 
            "comment": "", 
            "country": "", 
            "floor": "", 
            "latitude": "", 
            "longitude": "", 
            "meta_type": "", 
            "name": "", 
            "node_type": "", 
            "owner_id": "", 
            "postcode": "", 
            "responsible_for": "", 
            "room": "", 
            "site_type": "", 
            "telenor_subscription_id": ""
        }, 
        "name": "", 
        "version": 1
    }
}
'''

def get_node(name, node_type, meta_type):
    '''
    Gets or creates a NodeHandle with the provided name.
    Returns the NodeHandles node.
    '''
    name = nt.normalize_whitespace(name)
    node_handle = nt.get_unique_node_handle(nc.neo4jdb, name, node_type, 
                                            meta_type)
    node = node_handle.get_node()
    return node

def consume_site_csv(json_list):
    '''
    Inserts the data collected with NOCLook csv producer.
    '''
    # Add all properties except the ones with "special keys".
    for i in json_list:
        node_type = i['host']['csv_producer']['node_type'].title()
        meta_type = i['host']['csv_producer']['meta_type'].lower()
        nh = nt.get_unique_node_handle(nc.neo4jdb, i['host']['name'], node_type, 
                                       meta_type)
        node = nh.get_node()
        h.set_noclook_auto_manage(nc.neo4jdb, node, False)
        special_keys = ['comment', 'responsible_for', 'meta_type']
        host_info = i['host']['csv_producer']
        for key in host_info:
            if key not in special_keys:
                value = host_info.get(key, None)
                if value:
                    with nc.neo4jdb.transaction:
                        node[key] = value
        # Handle the special data
        for key in special_keys:
            value = host_info.get(key, None)
            if value:
                if key == 'responsible_for':
                    responsible_node = get_node(value, 'Site Owner', 'relation')
                    h.set_noclook_auto_manage(nc.neo4jdb, responsible_node,
                                               False)
                    rel = nc.create_relationship(nc.neo4jdb,
                                                          responsible_node, 
                                                          node, 
                                                          'Responsible_for')
                    h.set_noclook_auto_manage(nc.neo4jdb, rel, False)
                if key == 'comment':
                    nt.set_comment(nh, value)
                if key == 'meta_type':
                    pass # This is saved in the NodeHandle
        # Try to match equipment against sites
        search_index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
        matching_nodes = search_index.query('name', '*%s*' % i['host']['name']) 
        for equip_node in matching_nodes:
            if equip_node['node_type'] in ['Optical Node', 'Router']:
                rel = nc.create_relationship(nc.neo4jdb, equip_node,
                                                      node, 'Located_in')
                h.set_noclook_auto_manage(nc.neo4jdb, rel, False)
   
def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-D', nargs='?',
        help='Path to the json data.')

    args = parser.parse_args()
    # Start time
    start = datetime.datetime.now()
    timestamp_start = datetime.datetime.strftime(start,
        '%b %d %H:%M:%S')
    print '%s noclook_consumer.py was started.' % timestamp_start
    # Insert data from known data sources if option -I was used
    if args.D:
        print 'Loading data...'
        data = nt.load_json(args.D)
        print 'Inserting data...'
        consume_site_csv(data)
        print 'noclook consume done.'
    else:
        print 'Use -D to provide the path to the JSON files.'
        sys.exit(1)
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
