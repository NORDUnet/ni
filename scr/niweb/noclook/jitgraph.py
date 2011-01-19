import json
import neo4jclient

# Color and shape settings for know node types
# Physical
PHYSICAL = {'$type': 'rectangle',
        '$color': '#4876FF',
        '$height': '50',
        '$width': '50',
        '$dim': '10'}
# Logical
LOGICAL = {'$type': 'circle',
        '$color': '#70DB93',
        '$height': '50',
        '$width': '50',
        '$dim': '30'}
# Organisations
RELATION = {'$type': 'star',
        '$color': '#8A2BE2',
        '$height': '50',
        '$width': '50',
        '$dim': '20'}
# Locations
LOCATION = {'$type': 'ellipse',
        '$color': '#CD7F32',
        '$height': '50',
        '$width': '50',
        '$dim': '10'}

def get_jit_node(node):
    '''
    Creates the data structure for JSON export from a neo4j node.

    Return None for nodes that should not be part of the visualization.

    {'id': unique_id, 'name': node_name, 'data':{}, 'adjacencies':[]}
    '''
    structure = {'id': node.id,
                'name': '%s %s' % (node['type'], node['name']),
                'data':{
                    '$type': 'triangle',
                    '$color': '#EE3B3B', # Red
                    '$height': '50',
                    '$width': '50',
                    '$dim': '10',
                    'node_type': node['type']
                },
                'adjacencies':[]
                }

    # Set node specific apperance
    nc = neo4jclient.Neo4jClient()
    meta_type = nc.get_node_meta_type(node)
    if meta_type == 'physical':
        structure['data'].update(PHYSICAL)
    elif meta_type == 'logical':
        structure['data'].update(LOGICAL)
    elif meta_type == 'relation':
        structure['data'].update(RELATION)
    elif meta_type == 'location':
        structure['data'].update(LOCATION)

    # This is needed to be able to show meta nodes
    try:
        structure['data']['node_handle'] = node['handle_id']
    except KeyError:
        structure['data']['node_handle'] = None

    return structure

def get_directed_adjacencie(rel):
    '''
    Creates the data structure for JSON export from the relationship.

    {'nodeTo': unique_id, 'nodeFrom': unique_id, 'data':{}}
    '''
    structure = {'nodeTo': rel.end.id,
                'nodeFrom': rel.start.id,
                'data':{
                    # JIT data
                    '$type': 'arrow',
                    '$color': '#000000'}}

    return structure

def create_graph_list(root_node):
    '''
    Creates a data structure from the root node and adjacent nodes.
    This will be done in a special way for known node types else a
    generic way will be used.

    [{'id': unique_id,
    'name': node_name,
    'data':{},
    'adjacencies':[
        {'nodeTo': unique_id,
        'nodeFrom': unique_id,
        'data':{}}
    ]}]
    '''
    graph_list = []
    jit_root = get_jit_node(root_node)
    for rel in root_node.relationships.all():
        if rel.start.id != root_node.id:
            node = get_jit_node(rel.start)
        else:
            node = get_jit_node(rel.end)
        jit_root['adjacencies'].append(get_directed_adjacencie(rel))
        node['adjacencies'].append(get_directed_adjacencie(rel))
        graph_list.append(node)
    graph_list.append(jit_root)

    # Remove all None items from the list
    #graph_list = filter(lambda x: x is not None, graph_list)
    return graph_list

def get_json(root_node):
    '''
    Converts a graph_list to JSON and returns the JSON string.
    '''
    graph_list = create_graph_list(root_node)
    return json.dumps(graph_list)
