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
import norduni_client as nc
import noclook_consumer as nt
from memorymonitor import MemoryMonitor # DEBUG

'''
This script is used for adding the objects collected with the
NERDS producers to the noclook database viewer.
'''

def insert_services(service_dict, node_id):
    '''
    Takes a dictionary of services and a node id for a host. Gets or creates a 
    service and makes a Depends_on relationship between the service and host.
    
    Example service_dict:
    {"ipv4": {
        "127.0.0.1": {
            "tcp": {
                "1025": {
                    "product": "Microsoft Windows RPC", 
                    "confidence": "10", 
                    "name": "msrpc", 
                    "proto": "unknown"}, 
                "1029": {
                    "product": "Microsoft Windows RPC over HTTP", 
                    "confidence": "10", 
                    "version": "1.0", 
                    "name": "ncacn_http", 
                    "proto": "unknown"}, 
                }
            }
        }
    }
    '''
    node_type = "Host Service"
    meta_type = 'logical'
    host_node = nc.get_node_by_id(node_id)
    service_nodes = []
    memory_mon = MemoryMonitor('lundberg') # DEBUG 
    for key in service_dict.keys():
        print 'for key in service_dict.keys():' # DEBUG
        print host_node['name'] # DEBUG
        ipv = key
        print ipv # DEBUG
        for key in service_dict[ipv].keys():
            address = key
            print address # DEBUG
            for key in service_dict[ipv][address].keys():
                protocol = key
                print protocol # DEBUG
                for key in service_dict[ipv][address][protocol].keys():
                    print 'for key in service_dict[ipv][address][protocol].keys():' # DEBUG
                    port = key
                    print port # DEBUG
                    service = service_dict[ipv][address][protocol][port]
                    node_handle = nt.get_unique_node_handle(service['name'], 
                                                            node_type, 
                                                            meta_type)
                    service_node = node_handle.get_node()
                    service_nodes.append(service_node)
                    print 'service_node id: %d' % service_node.id # DEBUG
                    # Get already existing relationships between the two nodes
                    rels = nc.get_relationships(service_node, host_node, # SLOW PART
                                                'Depends_on')
                    create = True
                    for rel in rels:
                        print 'for rel in rels:' # DEBUG
                        if rel['ip_address'] == address and \
                        rel['protocol'] == protocol and rel['port'] == port:
                            create = False
                            break
                    if create:
                        # Make a relationship between the service and host
                        new_rel = nc.make_suitable_relationship(service_node, 
                                                        host_node, 'Depends_on')
                        new_rel['ip_address'] = address
                        new_rel['protocol'] = protocol
                        new_rel['port'] = port
                        for key, value in service.items():
                            print 'for key, value in service.items():' # DEBUG
                            new_rel[key] = value
                        print 'new_rel id: %d' % new_rel.id # DEBUG
    print 'All hosts services done.' # DEBUG
    print 'Used_memory, %d' % memory_mon.usage() # DEBUG
    return service_nodes

def insert_nmap(json_list):
    '''
    Inserts the data loaded from the json files created by
    the nerds producer nmap_services.
    '''
    node_type = "Host"
    meta_type = 'physical'
    # Insert the host
    for i in json_list:
        print 'for i in json_list:' # DEBUG
        name = i['host']['name']
        hostnames = json.dumps(i['host']['hostnames'])
        addresses = json.dumps(i['host']['addrs'])
        # Create the NodeHandle and the Node
        node_handle = nt.get_unique_node_handle(name, node_type, meta_type)
        # Set Node attributes
        node = node_handle.get_node()
        node['hostnames'] = hostnames
        node['addresses'] = addresses
        try:
            insert_services(i['host']['services'], node.id)
        except KeyError:
            pass

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
        nmap_services_data = config.get('data', 'nmap_services')
        if nmap_services_data:
            insert_nmap(nt.load_json(nmap_services_data))
    return 0

if __name__ == '__main__':
    main()
