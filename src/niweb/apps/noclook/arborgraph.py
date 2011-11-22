# -*- coding: utf-8 -*-
"""
Created on Thu Nov 10 14:52:53 2011

@author: lundberg
"""

import json
import norduni_client as nc

# Color and shape settings for know node types
# http://thejit.org/static/v20/Docs/files/Options/Options-Node-js.html
# Meta nodes
META = {'color': '#000000'}
# Physical
PHYSICAL = {'color': '#00CC00'}
# Logical
LOGICAL = {'color': '#007FFF'}
# Organisations
RELATION = {'color': '#FF9900'}
# Locations
LOCATION = {'color': '#FF4040'}

# Relations that should be traversed for a node type
#LOGICAL_TYPES = [nc.Undirected.Provides,
#                nc.Undirected.Uses,
#                nc.Undirected.Depends_on]
#
#PHYSICAL_TYPES = [nc.Undirected.Has,
#                nc.Undirected.Connected_to,
#                nc.Undirected.Depends_on,
#                nc.Undirected.Responsible_for,
#                nc.Undirected.Located_in]
#
#RELATION_TYPES = [nc.Undirected.Provides,
#                nc.Undirected.Uses,
#                nc.Undirected.Responsible_for]
#
#LOCATION_TYPES = [nc.Undirected.Has,
#                nc.Undirected.Responsible_for,
#                nc.Undirected.Located_in]

def get_arbor_node(node):
    '''
    Creates the data structure for JSON export from a neo4j node.

    Return None for nodes that should not be part of the visualization.

    {id: {
        "color": "", 
        "label": "", 
        "data": {
            "node_handle": "", 
            "node_type": ""
        }
    }}
    '''
    structure = {
        node.id: {
            'color': '',
            'label': '%s %s' % (node['node_type'], node['name']),
            'mass': 1,
            'data':{}
        }
    }
    # Set node specific apperance
    if node['node_type'] == 'meta':
        structure[node.id].update(META)
        structure[node.id]['data']['node_handle'] = None
    else:
        meta_type = nc.get_node_meta_type(node)
        if meta_type == 'physical':
            structure[node.id].update(PHYSICAL)
        elif meta_type == 'logical':
            structure[node.id].update(LOGICAL)
        elif meta_type == 'relation':
            structure[node.id].update(RELATION)
        elif meta_type == 'location':
            structure[node.id].update(LOCATION)
            #structure[node.id].update({'p': {
            #                            'x': node.latitude,
            #                            'y': node.longitude
            #                            }
            #                        })
    return structure

def get_directed_adjacencie(rel):
    '''
    Creates the data structure for JSON export from the relationship.

    {id: {
        "other_id": {
            "directed": true, 
            "label": ""
        }
        "other_id": {
            "directed": true, 
            "label": ""
        }
    }}
    '''
    structure = { 
        rel.start.id: {
            rel.end.id: {
                'directed': True,
                'label': str(rel.type).replace('_', ' ')
            }
        }
    }
    return structure

#def traverse_relationships(root_node, types, graph_list):
#    '''
#    Traverse the relationship we want and add the nodes and
#    adjacencies to the JSON structure.
#    '''
#    for rel in root_node.traverse(returns='relationship', types=types):
#        jit_node_start = get_jit_node(rel.start)
#        jit_node_end = get_jit_node(rel.end)
#        jit_node_start['adjacencies'].append(
#                                        get_directed_adjacencie(rel))
#        jit_node_end['adjacencies'].append(
#                                        get_directed_adjacencie(rel))
#        graph_list.append(jit_node_start)
#        graph_list.append(jit_node_end)
#    return graph_list

def create_generic_graph(root_node, graph_dict = None):
    '''
    Creates a data structure from the root node and adjacent nodes.
    This will be done in a special way for known node types else a
    generic way will be used.

    {"nodes": {
        id: {
            "color": "",
            "label": ""
        },
    "edges": {
        id: {
            "other_id": {
                "directed": true, 
                "label": ""
            }
        }
    }
    '''
    if not graph_dict:
        graph_dict = {'nodes': {}, 'edges': {}}
    # Generic graph dict
    arbor_root = get_arbor_node(root_node)
    graph_dict['nodes'].update(arbor_root)
    for rel in root_node.relationships:
        if rel.type.toString() != 'Contains':
            if rel.start.id == root_node.id:
                arbor_node = get_arbor_node(rel.end)
            else:
                arbor_node = get_arbor_node(rel.start)
            graph_dict['nodes'].update(arbor_node)
            arbor_edge = get_directed_adjacencie(rel)
            key = arbor_edge.keys()[0] # The only key in arbor_edge
            if graph_dict['edges'].has_key(key):
                graph_dict['edges'][key].update(arbor_edge[key])
            else:
                graph_dict['edges'].update(arbor_edge)
    return graph_dict

def get_json(graph_dict):
    '''
    Converts a graph_list to JSON and returns the JSON string.
    '''
    #return json.dumps(graph_dict)
    return json.dumps(graph_dict, indent=4)