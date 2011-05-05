#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       norduni_client.py
#
#       Copyright 2011 Johan Lundberg <lundberg@nordu.net>
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

import client # https://github.com/versae/neo4j-rest-client/
from django.conf import settings as django_settings
from django.template.defaultfilters import slugify

'''
This is an extension to the Neo4j REST client made by Versae which will make it
easier to add and retrive data to a Neo4j database according to the NORDUnet 
Network Inventory data model.

More information about NORDUnet Network Inventory: 
https://portal.nordu.net/display/opsforum/NORDUnet+Network+Inventory
'''

NEO4J_URI = django_settings.NEO4J_RESOURCE_URI

Outgoing = client.Outgoing
Incoming = client.Incoming
Undirected = client.Undirected

def normalize_whitespace(s):
    '''
    Removes leading and ending whitespace from a string.
    '''
    return ' '.join(s.split())

def open_db(uri):
    '''
    Open or create a Neo4j database in the supplied path.
    '''
    return client.GraphDatabase(uri)

def create_node(n='', t=''):
    '''
    Creates a node with the mandatory attributes name and type.
    '''
    db = open_db(NEO4J_URI)
    n = normalize_whitespace(n)
    t = normalize_whitespace(t)
    return db.node(name=n, node_type=t)
    
def get_node_by_id(node_id):
    '''
    Returns the node with the supplied id or none if it doesn't exist.
    '''
    db = open_db(NEO4J_URI)
    return db.nodes.get(int(node_id), None)

def delete_node(node_id):
    '''
    Deletes the node with the supplied id and returns True. Returns False
    if the node wasn't found.
    '''
    node = get_node_by_id(node_id)
    if node:
        for rel in node.relationships.all():
            rel.delete()
        node.delete()
        return True
    return False
    
def get_node_url(node_id):
    '''
    Returns a relative url to a node.
    '''
    node = get_node_by_id(node_id)
    return '%s%s/%d/' % (django_settings.NIWEB_URL, slugify(node['node_type']),
                                                    node['handle_id'])

def get_root_node():
    '''
    Returns the root node, also known as node[0].
    '''
    return get_node_by_id(0)
    
def get_node_by_value(node_value, meta_node_name=None,
                                                node_property=None):
    '''
    Traverses the meta node, if any, else it traverses all
    available meta nodes and compares the property of the nodes
    with the supplied strings and returns the ones matching.
    '''
    if meta_node_name is not None:
        meta_node = get_meta_node(meta_node_name)
        meta_node_list = [meta_node] # It's easy to loop with lists
    else:
        meta_node_list = get_all_meta_nodes()
    node_list = []
    for meta_node in meta_node_list:
        for node in meta_node.traverse():
            if node_property is None: # Compare all values
                for key in node.properties:
                    if node.properties[key] == node_value:
                        node_list.append(node)
            else: # Compare the supplied property value if it exists
                try:
                    value = node.properties[node_property]
                    if value == node_value:
                        node_list.append(node)
                except KeyError:
                    pass
    return node_list
        
def get_all_nodes():
    '''
    Returns all nodes in the database in a list. 
    '''
    root = get_root_node()
    nodes = [root]
    for meta_node in root.traverse():
        nodes.extend(meta_node.traverse())
    return list(set(nodes))
        
def get_all_relationships():
    '''
    Returns all relationships in the database in a list.
    '''
    relationships = []
    for node in get_all_nodes():
        relationships.extend(node.relationships.all())
    return list(set(relationships))

def get_node_meta_type(node):
    '''
    Returns the meta type of the supplied node as a string.
    '''
    rel = node.relationships.incoming(types=['Consists_of',
                                                    'Contains'])[0]
    return rel.start['name']

def get_root_parent(node, rel_type):
    '''
    Returns the nodes most top parent (not meta nodes or root node).
    '''
    node_list = node.traverse(types=[rel_type])
    for node in node_list:
        for rel in node.relationships.all():
            if rel.type == 'Contains': # Doesnt all nodes have this rel?
                return node
    return None

def get_all_meta_nodes():
    '''
    Will return all available meta nodes.
    '''
    root = get_root_node()
    rels = root.relationships.outgoing(["Consists_of"])
    meta_node_list = []
    for rel in rels:
        meta_node_list.append(rel.end)
    return meta_node_list

def get_meta_node(meta_node_name):
    '''
    Will return the meta node requested or create it and return it.
    '''
    root = get_root_node()
    rels = root.relationships.outgoing(["Consists_of"])
    for rel in rels:
        if rel.end['name'] == meta_node_name.lower():
            return rel.end
    # No node with requested name found
    n = create_node(meta_node_name.lower(), 'meta')
    root.Consists_of(n)
    return n
        
def get_suitable_nodes(node):
    '''
    Takes a reference node and returns all nodes that is suitable for a
    relationship with that node.
    
    Returns a dictionary with the suitable nodes in lists separated by 
    meta_type.
    '''
    meta_type = get_node_meta_type(node).lower()
    
    # Create and fill the dictionary with all nodes
    suitable_types = {'physical': [], 'logical': [], 
                      'relation': [], 'location': []}
    for key in suitable_types:
        meta_node = get_meta_node(key)
        suitable_types[key] = meta_node.traverse(Outgoing.Contains)
    # Remove the reference node, can't have relationship with yourself        
    suitable_types[meta_type].remove(node)
    # Unreference the types of nodes that are un suitable                  
    if meta_type == 'location':
        suitable_types['location'] = []
        suitable_types['logical'] = []
    elif meta_type == 'logical':
        suitable_types['location'] = []
    elif meta_type == 'relation':
        suitable_types['relation'] = []
    return suitable_types
        
def make_suitable_relationship(node, other_node, rel_type):
    '''
    Makes a relationship from node to other_node depending on which
    meta_type the nodes sent in are. Returns the relationship or None
    if no relationship was made.
    '''
    meta_type = get_node_meta_type(node)
    other_meta_type = get_node_meta_type(other_node)
    rel = None
    if meta_type == 'location':                # Location
        if other_meta_type == 'location':
            rel = node.Has(other_node)
    elif meta_type == 'logical':               # Logical
        if other_meta_type == 'logical':
            rel = node.Depends_on(other_node)
        elif other_meta_type == 'physical':
            rel = node.Depends_on(other_node)
    elif meta_type == 'relation':              # Relation
        if other_meta_type == 'logical':
            if rel_type == 'Uses':
                rel = node.Uses(other_node)
            elif rel_type == 'Provides':
                rel = node.Provides(other_node)
        elif other_meta_type == 'location':
            rel = node.Responsible_for(other_node)
        elif other_meta_type == 'physical':
            rel = node.Responsible_for(other_node)
    elif meta_type == 'physical':              # Physical
        if other_meta_type == 'physical':
            if rel_type == 'Has':
                rel = node.Has(other_node)
            if rel_type == 'Connected_to':
                rel = node.Connected_to(other_node)
        elif other_meta_type == 'Location':
            rel = node.Located_in(other_node)
    return rel
        
def get_relationship_by_id(rel_id, node=None):
    '''
    Returns the relationship with the supplied id.
    '''
    if node:
        for rel in node.relationships.all():
            if rel.id == int(rel_id):
                return rel
    else:
        for rel in get_all_relationships():
            if rel.id == int(rel_id):
                return rel
    return None

def get_relationships(n1, n2, rel_type=None):
    '''
    Takes a start and an end node with an optional relationship
    type.
    Returns the relationsships between the nodes or an empty list.
    '''
    rel_list = []
    for rel in n1.relationships.all():
        if (rel.start.id == n1.id and rel.end.id == n2.id) or \
        (rel.start.id == n2.id and rel.end.id == n1.id):
            if rel_type:
                if rel.type == rel_type:
                    rel_list.append(rel)
            else:
                rel_list.append(rel)
    return rel_list

def update_node_properties(node_id, new_properties):
    '''
    Take a node and a dictionary of properties. Updates the
    node and returns it.
    '''
    node = get_node_by_id(node_id)
    # We might want to do a better check of the data...
    for key, value in new_properties.items():
        fixed_key = key.replace(' ','_').lower() # No spaces or caps
        if value:
            node[fixed_key] = normalize_whitespace(value)
        elif fixed_key in node.properties:
            del node[fixed_key]
    return node

def update_relationship_properties(node_id, rel_id, new_properties):
    '''
    Updates the properties of a relationship with the supplied dictionary.
    '''
    node = get_node_by_id(node_id)
    rel = get_relationship_by_id(node, rel_id)
    for key, value in new_properties.items():
        fixed_key = key.replace(' ','_').lower() # No ' ' or caps
        if value:
            rel[fixed_key] = normalize_whitespace(value)
        elif fixed_key in rel.properties:
            del rel[fixed_key]
    return rel

def main():

    def test_db_setup():
        import os
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
        print 'Testing read and write for Neo4j REST database at %s.' \
                                        % django_settings.NEO4J_RESOURCE_URI
        print 'Next line should be "Root 0".'
        n = get_node_by_id('0')
        n['name'] = 'Root'
        print n['name'], n.id

    test_db_setup()
    return 0

if __name__ == '__main__':
    main()
