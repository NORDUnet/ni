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
import datetime
import argparse

## Need to change this path depending on where the Django project is
## located.
#path = '/var/norduni/src/niweb/'
path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
import noclook_consumer as nt
import norduni_client as nc

'''
This script is used for adding the objects collected with the
NERDS csv producer from the NORDUnet host inventory spreadsheets.

{
    "host": {
        "csv_producer": {
            "aliases": "", 
            "backup": "", 
            "comment": "", 
            "cpu": "", 
            "end_support": "", 
            "hdd": "", 
            "ipv4_address": "", 
            "ipv6_address": "", 
            "location": "", 
            "meta_type": "", 
            "model": "", 
            "name": "", 
            "node_type": "", 
            "os": "", 
            "os_version": "", 
            "provider": "", 
            "ram": "", 
            "service": "", 
            "service_tag": "", 
            "status": "", 
            "user": "", 
            "vendor": ""
        }, 
        "name": "host.example.com", 
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
    node_handle = nt.get_unique_node_handle(name, node_type, 
                                            meta_type)
    node = node_handle.get_node()
    node['noclook_auto_manage'] = False
    node['noclook_last_seen'] = datetime.datetime.now().isoformat()
    return node

def consume_host_csv(json_list):
    '''
    Inserts the data collected with NOCLook csv producer.
    '''
    # Add all properties except the ones with "special keys".
    node_type = "Host"
    meta_type = 'logical'
    for i in json_list:
        nh = nt.get_unique_node_handle(i['host']['name'], node_type, 
                                       meta_type)
        node = nh.get_node()
        special_keys = ['ipv4_address', 'ipv6_address', 'comment', 'service',
                        'aliases', 'hostnames', 'user', 'provider', 'meta_type']
        host_info = i['host']['csv_producer']
        for key in host_info:
            if key not in special_keys:
                value = host_info.get(key, None)
                if value:
                    node[key] = value
        # Handle the special data
        for key in special_keys:
            value = host_info.get(key, None)
            if value:
                if key == 'hostnames' or key == 'aliases':
                    nc.merge_properties(node.id, 'hostnames', value.split(','))
                if key == 'ipv4_address' or key == 'ipv6_address':
                    nc.merge_properties(node.id, 'addresses', value.split(','))
                if key == 'service':
                    for service in value.split(','):
                        service_node = get_node(service, 'Host Service', 
                                                'logical')
                        nc.make_suitable_relationship(service_node, 
                                                        node, 'Depends_on')
                if key == 'user':
                    user_node = get_node(value, 'Host User', 'relation')
                    nc.make_suitable_relationship(user_node, node, 'Uses')
                if key == 'provider':
                    provider_node = get_node(value, 'Host Provider', 'relation')
                    nc.make_suitable_relationship(provider_node, 
                                                        node, 'Provides')
                if key == 'comment':
                    nt.set_comment(nh, value)
                if key == 'meta_type':
                    pass # This is saved in the NodeHandle
   
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
        consume_host_csv(data)
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
