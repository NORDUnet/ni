import json
import neo4jclient

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

def get_jit_node(node):
    '''
    Creates the data structure for JSON export from a neo4j node.

    Return None for nodes that should not be part of the visualization.

    {'id': unique_id, 'name': node_name, 'data':{}, 'adjacencies':[]}
    '''
    structure = {'id': node.id,
                'name': '%s %s' % (node['type'], node['name']),
                'data':{
                    # JIT data
                    '$type': 'triangle',
                    '$color': '#EE3B3B', # Red
                    '$dim': '15',
                    # Other data
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
                    '$type': 'line',
                    '$color': '#000000'}}

    return structure

def traverse_relationships(root_node, ttype, rtype):
    '''
    Traverse the relationship we want and add the nodes and
    adjacencies to the JSON structure.
    ttype is traversal type:    nc.Undirected.*
                                nc.Outgoing.*
                                nc.Incoming.*
    rtype is the relation type as a string.
    '''
    nc = neo4jclient.Neo4jClient()
    graph_list = []
    traverse_list = root_node.traverse(types=[ttype])
    traverse_list.append(root_node)
    # Needs to be done differently, to slooow.
    for node in traverse_list:
        for node2 in traverse_list:
            for rel in nc.get_relationships(node, node2, rtype):
                jit_node = get_jit_node(node)
                jit_node['adjacencies'].append(
                                        get_directed_adjacencie(rel))
                jit_node2 = get_jit_node(node2)
                jit_node2['adjacencies'].append(
                                        get_directed_adjacencie(rel))
                graph_list.append(jit_node)
                graph_list.append(jit_node2)
    return graph_list

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
    nc = neo4jclient.Neo4jClient()
    # Create graph lists for known node types
    meta_type = nc.get_node_meta_type(root_node)
    if meta_type == 'physical':
        graph_list = create_physical_graph_list(root_node)
    elif meta_type == 'logical':
        graph_list = create_logical_graph_list(root_node)
    elif meta_type == 'relation':
        graph_list = create_relation_graph_list(root_node)
    elif meta_type == 'location':
        graph_list = create_location_graph_list(root_node)
    else:
        graph_list = []
        jit_root = get_jit_node(root_node)
        for rel in root_node.relationships.all():
            if rel.start.id != root_node.id:
                jit_node = get_jit_node(rel.start)
            else:
                jit_node = get_jit_node(rel.end)
            jit_root['adjacencies'].append(get_directed_adjacencie(rel))
            jit_node['adjacencies'].append(get_directed_adjacencie(rel))
            graph_list.append(node)
        graph_list.append(jit_root)

    return graph_list

def create_physical_graph_list(root_node):
    '''
    Creates a graph_list that is specialized for visualizing a physical
    node and its adjacencies.
    '''
    nc = neo4jclient.Neo4jClient()
    graph_list = []
    graph_list.extend(traverse_relationships(root_node,
                                                nc.Undirected.Has,
                                                'Has'))
    graph_list.extend(traverse_relationships(root_node,
                                            nc.Undirected.Connected_to,
                                            'Connected_to'))
    graph_list.extend(traverse_relationships(root_node,
                                            nc.Undirected.Depends_on,
                                            'Depends_on'))
    graph_list.extend(traverse_relationships(root_node,
                                        nc.Undirected.Responsible_for,
                                        'Responsible_for'))
    graph_list.extend(traverse_relationships(root_node,
                                        nc.Undirected.Located_in,
                                        'Located_in'))
    return graph_list

def create_logical_graph_list(root_node):
    '''
    Creates a graph_list that is specialized for visualizing a physical
    node and its adjacencies.
    '''
    nc = neo4jclient.Neo4jClient()
    graph_list = []
    graph_list.extend(traverse_relationships(root_node,
                                                nc.Undirected.Provides,
                                                'Provides'))
    graph_list.extend(traverse_relationships(root_node,
                                            nc.Undirected.Uses,
                                            'Uses'))
    graph_list.extend(traverse_relationships(root_node,
                                            nc.Undirected.Depends_on,
                                            'Depends_on'))
    return graph_list

def create_relation_graph_list(root_node):
    '''
    Creates a graph_list that is specialized for visualizing a physical
    node and its adjacencies.
    '''
    nc = neo4jclient.Neo4jClient()
    graph_list = []
    graph_list.extend(traverse_relationships(root_node,
                                                nc.Undirected.Provides,
                                                'Provides'))
    graph_list.extend(traverse_relationships(root_node,
                                            nc.Undirected.Uses,
                                            'Uses'))
    graph_list.extend(traverse_relationships(root_node,
                                        nc.Undirected.Responsible_for,
                                        'Responsible_for'))
    return graph_list

def create_location_graph_list(root_node):
    '''
    Creates a graph_list that is specialized for visualizing a physical
    node and its adjacencies.
    '''
    nc = neo4jclient.Neo4jClient()
    graph_list = []
    graph_list.extend(traverse_relationships(root_node,
                                                nc.Undirected.Has,
                                                'Has'))
    graph_list.extend(traverse_relationships(root_node,
                                        nc.Undirected.Responsible_for,
                                        'Responsible_for'))
    graph_list.extend(traverse_relationships(root_node,
                                        nc.Undirected.Located_in,
                                        'Located_in'))
    return graph_list

def get_json(root_node):
    '''
    Converts a graph_list to JSON and returns the JSON string.
    '''
    graph_list = create_graph_list(root_node)
    return json.dumps(graph_list)
