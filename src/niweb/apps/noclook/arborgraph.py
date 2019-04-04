# -*- coding: utf-8 -*-
"""
Created on Thu Nov 10 14:52:53 2011

@author: lundberg
"""

import json
from .helpers import labels_to_node_type, get_node_urls
import norduniclient as nc
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)

# Color and shape settings for know node types
# http://thejit.org/static/v20/Docs/files/Options/Options-Node-js.html
# Meta nodes
COLOR_MAP = {
    'Meta:': '#000000',
    'Physical': '#00CC00',
    'Logical': '#007FFF',
    'Relation': '#FF9900',
    'Location': '#FF4040',
}


def to_arbor_node(raw_node, fixed=False):
    """
    Creates the data structure for JSON export from a raw neo4j node.

    Return None for nodes that should not be part of the visualization.

    {id: {
        "color": "",
        "label": "",
    }}
    """
    handle_id = raw_node.properties['handle_id']
    meta_type = next(l for l in raw_node.labels if l in nc.core.META_TYPES)
    node_type = labels_to_node_type(raw_node.labels)
    node_name = raw_node.properties['name']
    structure = {
        handle_id: {
            'color': COLOR_MAP.get(meta_type, ''),
            'label': '%s %s' % (node_type, node_name),
        }
    }
    if fixed:
        structure[handle_id]['fixed'] = fixed
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
        graph_dict = {'nodes': defaultdict(dict), 'edges': defaultdict(dict)}
    # Generic graph dict
    graph_dict['nodes'].update({
        root_node.handle_id: {
            'color': COLOR_MAP[root_node.meta_type],
            'label': '{} {}'.format(labels_to_node_type(root_node.labels), root_node.data['name']),
            'fixed': True,
        }
    })

    q = """
        MATCH (n:Node {handle_id: {handle_id}})-[r]->(end)
        RETURN type(r) as relation, collect(distinct end) as nodes
        """
    relations = nc.query_to_list(nc.graphdb.manager, q, handle_id=root_node.handle_id)
    q = """
        MATCH (n:Node {handle_id: {handle_id}})<-[r]-(start)
        RETURN type(r) as relation, collect(distinct start) as nodes
        """
    dependencies = nc.query_to_list(nc.graphdb.manager, q, handle_id=root_node.handle_id)
    for rel in relations:
        rel_type = rel['relation'].replace('_', ' ')
        for node in rel['nodes']:
            graph_dict['nodes'].update(to_arbor_node(node))
        graph_dict['edges'][root_node.handle_id].update({n.properties['handle_id']: {"directed": True, "label": rel_type} for n in rel['nodes']})

    for dep in dependencies:
        rel_type = dep['relation'].replace('_', ' ')
        for node in dep['nodes']:
            graph_dict['nodes'].update(to_arbor_node(node))
            graph_dict['edges'][node.properties['handle_id']].update({root_node.handle_id: {"directed": True, "label": rel_type}})
    urls = get_node_urls(root_node, relations, dependencies)
    for node in graph_dict['nodes']:
        graph_dict['nodes'][node]['url'] = urls.get(node)
    return graph_dict


def get_json(graph_dict):
    """
    Converts a graph_list to JSON and returns the JSON string.
    """
    return json.dumps(graph_dict, indent=4)
