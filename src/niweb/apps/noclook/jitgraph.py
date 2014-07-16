import json
import norduniclient as nc

# Color and shape settings for know node types
# http://thejit.org/static/v20/Docs/files/Options/Options-Node-js.html
# Physical
PHYSICAL = {'$type': 'circle',
        '$color': '#00FF00',
        '$dim': '15'}
# Logical
LOGICAL = {'$type': 'circle',
        '$color': '#007FFF',
        '$dim': '15'}
# Organisations
RELATION = {'$type': 'circle',
        '$color': '#FFFF00',
        '$dim': '15'}
# Locations
LOCATION = {'$type': 'circle',
        '$color': '#FF4040',
        '$dim': '15'}

# Relations that should be traversed for a node type
LOGICAL_TYPES = [nc.Undirected.Provides,
                nc.Undirected.Uses,
                nc.Undirected.Depends_on]

PHYSICAL_TYPES = [nc.Undirected.Has,
                nc.Undirected.Connected_to,
                nc.Undirected.Depends_on,
                nc.Undirected.Responsible_for,
                nc.Undirected.Located_in]

RELATION_TYPES = [nc.Undirected.Provides,
                nc.Undirected.Uses,
                nc.Undirected.Responsible_for]

LOCATION_TYPES = [nc.Undirected.Has,
                nc.Undirected.Responsible_for,
                nc.Undirected.Located_in]

def get_jit_node(node):
    '''
    Creates the data structure for JSON export from a neo4j node.

    Return None for nodes that should not be part of the visualization.

    {'id': unique_id, 'name': node_name, 'data':{}, 'adjacencies':[]}
    '''
    structure = {'id': node.id,
                'name': '%s %s' % (node['node_type'], node['name']),
                'data':{
                    # JIT data
                    '$type': 'triangle',
                    '$color': '#EE3B3B', # Red
                    '$dim': '15',
                    # Other data
                    'node_type': node['node_type']
                },
                'adjacencies':[]
                }

    # Set node specific apperance
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
                    '$type': 'line',
                    '$color': '#000000',
                    # Other data
                    'relationship': str(rel.type).replace('_', ' ')}
                }

    return structure

def traverse_relationships(root_node, types, graph_list):
    '''
    Traverse the relationship we want and add the nodes and
    adjacencies to the JSON structure.
    '''
    for rel in root_node.traverse(returns='relationship', types=types):
        jit_node_start = get_jit_node(rel.start)
        jit_node_end = get_jit_node(rel.end)
        jit_node_start['adjacencies'].append(
                                        get_directed_adjacencie(rel))
        jit_node_end['adjacencies'].append(
                                        get_directed_adjacencie(rel))
        graph_list.append(jit_node_start)
        graph_list.append(jit_node_end)
    return graph_list

def create_graph_list(root_node, graph_list = None):
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
    if graph_list == None:
        graph_list = []
    # Create graph lists for known node types
    meta_type = nc.get_node_meta_type(root_node)
    if meta_type == 'physical':
        graph_list.extend(traverse_relationships(root_node,
                                                    PHYSICAL_TYPES,
                                                    graph_list))
    elif meta_type == 'logical':
        graph_list.extend(traverse_relationships(root_node,
                                                    LOGICAL_TYPES,
                                                    graph_list))
    elif meta_type == 'relation':
        graph_list.extend(traverse_relationships(root_node,
                                                    RELATION_TYPES,
                                                    graph_list))
    elif meta_type == 'location':
                graph_list.extend(traverse_relationships(root_node,
                                                    LOCATION_TYPES,
                                                    graph_list))
    else:
        # Generic graph list
        jit_root = get_jit_node(root_node)
        for rel in root_node.relationships.all():
            if rel.start.id != root_node.id:
                jit_node = get_jit_node(rel.start)
            else:
                jit_node = get_jit_node(rel.end)
            jit_root['adjacencies'].append(get_directed_adjacencie(rel))
            jit_node['adjacencies'].append(get_directed_adjacencie(rel))
            graph_list.append(jit_node)
        graph_list.append(jit_root)

    return graph_list

def get_json(root_node):
    '''
    Converts a graph_list to JSON and returns the JSON string.
    '''
    graph_list = create_graph_list(root_node)
    return json.dumps(graph_list)
