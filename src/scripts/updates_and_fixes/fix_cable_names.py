# -*- coding: utf-8 -*-
"""
Created on Fri Jan 13 10:16:53 2012

@author: lundberg
"""

import sys
import os

path = '/home/lundberg/norduni/src/niweb/'
path2 = '/home/lundberg/norduni/src/scripts/'
##
##
sys.path.append(os.path.abspath(path))
sys.path.append(os.path.abspath(path2))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from apps.noclook.models import NodeHandle
import norduniclient as nc
import noclook_consumer as nt

def normalize_whitespace(text):
    '''
    Remove redundant whitespace from a string.
    '''
    text = text.replace('"', '').replace("'", '')
    return ' '.join(text.split())

f = open('cable_list')
index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())

# Delete all cable nodes
index = nc.get_node_index(nc.neo4jdb, 'node_types')
hits = index['node_type']['Cable']
for node in hits:
    NodeHandle.objects.get(pk=node['handle_id']).delete()
    #nc.delete_node(nc.neo4jdb, node)

for line in f:
    #cable_name;optical_node_name;telenor_trunk_id;telenor_tn1_number;global_crossing_circuit_id
    #105-0041;NU-SSTS-ILA-01;105-0041;20811;123456789
    name_list = normalize_whitespace(line).split(';')
    cable_node_handle = nt.get_unique_node_handle(nc.neo4jdb, name_list[0], 
                                                  'Cable','physical')
    cable_node = cable_node_handle.get_node()
    nc.set_noclook_auto_manage(nc.neo4jdb, cable_node, True)
    with nc.neo4jdb.transaction:
        cable_node['cable_type'] = 'Fiber'
        if name_list[2] or name_list[3]:
            cable_node['telenor_trunk_id'] = name_list[2]
            cable_node['telenor_tn1_number'] = name_list[3]
        if name_list[4]:
            cable_node['global_crossing_circuit_id'] = name_list[4]
    optical_node_node_handle = nt.get_unique_node_handle(nc.neo4jdb, name_list[1], 
                                                  'Optical Node','physical')
    optical_node_node = optical_node_node_handle.get_node()    
    rel = nc.create_relationship(nc.neo4jdb, cable_node, optical_node_node,
                                          'Connected_to')
    nc.set_noclook_auto_manage(nc.neo4jdb, rel, True)