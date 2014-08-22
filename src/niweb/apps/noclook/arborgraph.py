# -*- coding: utf-8 -*-
"""
Created on Thu Nov 10 14:52:53 2011

@author: lundberg
"""

import json
from apps.noclook.helpers import get_node_url
import norduniclient as nc

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


def get_arbor_node(node):
    """
    Creates the data structure for JSON export from a neo4j node.

    Return None for nodes that should not be part of the visualization.

    {id: {
        "color": "", 
        "label": "", 
        "mass": 0,
    }}
    """
    structure = {
        node.handle_id: {
            'color': '',
            'label': '%s %s' % (node.labels[0], node.data['name']),
            'url': '%s' % get_node_url(node)
            #'mass': len(node.relationships),
        }
    }
    # Set node specific apperance
    meta_type = node.meta_type
    if meta_type == 'Physical':
        structure[node.handle_id].update(PHYSICAL)
    elif meta_type == 'Logical':
        structure[node.handle_id].update(LOGICAL)
    elif meta_type == 'Relation':
        structure[node.handle_id].update(RELATION)
        #structure[node.id].update({'x': 0, 'y': 0, 'fixed': True})
    elif meta_type == 'Location':
        structure[node.handle_id].update(LOCATION)
    return structure


def get_directed_adjacency(relationship):
    """
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
    """
    structure = {
        relationship.start.handle_id: {
            relationship.end.handle_id: {
                'directed': True,
                'label': relationship.type.replace('_', ' '),
                #'lenght': 1
            }
        }
    }
    return structure


def create_generic_graph(root_node, graph_dict=None):
    """
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
    """
    if not graph_dict:
        graph_dict = {'nodes': {}, 'edges': {}}
    # Generic graph dict
    arbor_root = get_arbor_node(root_node)
    graph_dict['nodes'].update(arbor_root)
    relationships = root_node.relationships
    for rel_type in relationships:
        for item in relationships[rel_type]:
            relationship = nc.get_relationship_model(nc.neo4jdb, item['relationship_id'])
            if relationship.start.handle_id == root_node.handle_id:
                arbor_node = get_arbor_node(relationship.end)
            else:
                arbor_node = get_arbor_node(relationship.start)
            graph_dict['nodes'].update(arbor_node)
            arbor_edge = get_directed_adjacency(relationship)
            key = arbor_edge.keys()[0] # The only key in arbor_edge
            if key in graph_dict['edges']:
                graph_dict['edges'][key].update(arbor_edge[key])
            else:
                graph_dict['edges'].update(arbor_edge)
    return graph_dict


def get_json(graph_dict):
    """
    Converts a graph_list to JSON and returns the JSON string.
    """
    #return json.dumps(graph_dict)
    return json.dumps(graph_dict, indent=4)