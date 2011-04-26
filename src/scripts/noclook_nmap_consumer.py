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

import os
import sys
import json
import argparse

## Need to change this path depending on where the Django project is
## located.
#path = '/var/norduni/src/niweb/'
path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import neo4jclient
import noclook_consumer as nt

'''
This script is used for adding the objects collected with the
NERDS producers to the noclook database viewer.
'''

def insert_nmap(json_list):
    '''
    Inserts the data loaded from the json files created by
    the nerds producer nmap_services.
    '''
    nc = neo4jclient.Neo4jClient()

    # Hard coded values that we can't get on the fly right now
    #user = User.objects.get(username="lundberg")
    node_type = "Host"
    meta_type = 'physical'

    # Insert the host
    for i in json_list:
        name = i['host']['name']
        hostnames = json.dumps(i['host']['hostnames'])
        addresses = json.dumps(i['host']['addrs'])
        try:
            services = json.dumps(i['host']['services'])
        except KeyError:
            services = 'None'

        # Create the NodeHandle and the Node
        node_handle = nt.get_unique_node_handle(name, node_type, meta_type)

        # Set Node attributes
        node = nc.get_node_by_id(node_handle.node_id)
        node['hostnames'] = hostnames
        node['addresses'] = addresses
        node['services'] = services


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?',
        help='Path to the configuration file.')
    args = parser.parse_args()
    
    # Load the configuration file
    if args.C == None:
        print 'Please provide a configuration file with -C.'
        sys.exit(1)
    else:
        config = nt.init_config(args.C)
        nmap_services_data = config.get('data', 'nmap_services')
        if nmap_services_data:
            insert_nmap(nt.load_json(nmap_services_data))
    return 0

if __name__ == '__main__':
    main()
