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

from neo4j import GraphDatabase, Uniqueness, Evaluation, OUTGOING, INCOMING, ANY
from django.conf import settings as django_settings
from django.template.defaultfilters import slugify
import json

'''
This started as an extension to the Neo4j REST client made by Versae, continued
as an extension for the official Neo4j python bindings when they were released
(Neo4j 1.5, http://docs.neo4j.org/chunked/milestone/python-embedded.html).

The goal is to make it easier to add and retrive data to a Neo4j database 
according to the NORDUnet Network Inventory data model.

More information about NORDUnet Network Inventory: 
https://portal.nordu.net/display/NI/
'''

NEO4J_URI = django_settings.NEO4J_RESOURCE_URI

# Helper functions
def normalize_whitespace(s):
    '''
    Removes leading and ending whitespace from a string.
    '''
    return ' '.join(s.split())
    
def lowerstr(s):
    '''
    Makes everything to a string and tries to make it lower case. Also
    normalizes whitespace.
    '''
    return normalize_whitespace(unicode(s).lower())
    
def is_meta_node(node):
    '''
    Returns True if the provided node is of node_type == meta.
    '''
    if node['node_type'] == 'meta':
        return True
    return False

def get_node_url(node):
    '''
    Returns a relative url to a node.
    '''
    return '%s%s/%d/' % (django_settings.NIWEB_URL, slugify(node['node_type']),
                                                    node['handle_id'])

# Core functions
def open_db(uri=NEO4J_URI):
    '''
    Open or create a Neo4j database in the supplied path.
    '''
    return GraphDatabase(uri)

def create_node(db, n='', t=''):
    '''
    Creates a node with the mandatory attributes name and type.
    '''
    n = normalize_whitespace(n)
    t = normalize_whitespace(t)
    with db.transaction:
        node = db.node(name=n, node_type=t)
        # Add the nodes name and type to indexes
        i1 = get_node_index(db, search_index_name())
        add_index_item(db, i1, node, 'name')
        i2 = get_node_index(db, 'node_types')
        add_index_item(db, i2, node, 'node_type')
    return node
    
def get_root_node(db):
    '''
    Returns the root node, also known as node[0].
    '''
    return db.reference_node

def get_node_by_id(db, node_id):
    '''
    Returns the node with the supplied id or None if it doesn't exist.
    '''
    with db.transaction:
        try:
            node = db.nodes.get(int(node_id))
        except KeyError:
            return None
    return node
    
def get_all_nodes(db):
    '''
    Returns all nodes in the database in a list. 
    '''
    root = get_root_node(db)
    nodes = [root]
    traverser = db.traversal().uniqueness(Uniqueness.NODE_GLOBAL).traverse(root)
    for node in traverser.nodes:
        nodes.append(node)
    return nodes
    
def get_relationship_by_id(db, rel_id):
    '''
    Returns the relationship with the supplied id.
    '''
    with db.transaction:
        try:
            rel = db.relationships[int(rel_id)]
        except KeyError:
            return None
    return rel
        
def get_all_relationships(db):
    '''
    Returns all relationships in the database in a list.
    '''
    root = get_root_node(db)
    relationships = []
    traverser = db.traversal().uniqueness(
                                Uniqueness.RELATIONSHIP_GLOBAL).traverse(root)
    for relationship in traverser.relationships:
        relationships.append(relationship)
    return relationships

def delete_node(db, node_id):
    '''
    Deletes the node with the supplied id and returns True. Returns False
    if the node wasn't found.
    '''
    node = get_node_by_id(db, node_id)
    if node:
        with db.transaction:
            for rel in node.relationships:
                rel.delete()
            node.delete()
            return True
    return False

# NORDUni functions
def get_meta_node(db, meta_node_name):
    '''
    Will return the meta node requested or create it and return it.
    '''
    def meta_name_evaluator(path):
        # Filter on meta node name
        if path.end['name'] == meta_node_name.lower():
            return Evaluation.INCLUDE_AND_PRUNE
        return Evaluation.EXCLUDE_AND_CONTINUE
    root = get_root_node(db)
    traverser = db.traversal().evaluator(meta_name_evaluator).traverse(root)
    try:
        meta_node = list(traverser.nodes)[0]
    except IndexError:
        # No node with requested name found, create it.
        with db.transaction:
            meta_node = create_node(db, meta_node_name.lower(), 'meta')
            root.Consists_of(meta_node)
    return meta_node

def get_all_meta_nodes(db):
    '''
    Will return all meta nodes.
    '''
    root = get_root_node(db)
    traverser = db.traversal().relationships('Consists_of').traverse(root)
    meta_node_list = list(traverser.nodes)
    return meta_node_list
    
def get_node_meta_type(node):
    '''
    Returns the meta type of the supplied node as a string.
    '''
    return node.Contains.single.start['name']

def get_root_parent(db, node):
    '''
    Returns the nodes most top parent (not meta nodes or root node).
    '''
    def top_parent_evaluator(path):
        # Filter on relationship type Contains.
        try:
            if path.last_relationship.type.name() == 'Contains':
                return Evaluation.INCLUDE_AND_PRUNE
        except AttributeError:
            pass
        return Evaluation.EXCLUDE_AND_CONTINUE
    traverser = db.traversal().evaluator(top_parent_evaluator).traverse(node)
    for path in traverser:
        return path.last_relationship.end
    
def get_node_by_value(db, node_value, node_property=None):
    '''
    Traverses the meta node, if any, else it traverses all
    available meta nodes and compares the property of the nodes
    with the supplied strings. Returns a list of matching nodes.
    '''
    def value_evaluator(path):
        # Filter on the nodes property values
        if node_property:
            # Compare supplied property
            properties = [node_property]
        else:
            # Compare all the nodes properties
            properties = list(path.end.keys())
        for p in properties:
            try:
                if lowerstr(path.end[p]) == lowerstr(node_value):
                    return Evaluation.INCLUDE_AND_CONTINUE
            except KeyError:
                    pass
        return Evaluation.EXCLUDE_AND_CONTINUE
    start_node = get_root_node(db)
    traverser = db.traversal().evaluator(value_evaluator).traverse(start_node)
    return list(traverser.nodes)

def get_indexed_node_by_value(db, node_value, node_type, node_property=None):
    '''
    Searches through the node_types index for nodes matching node_type and
    the value or property/value pair. Returns a list of matching nodes.
    '''
    node_types_index = get_node_index(db, 'node_types')
    hits = node_types_index.query('node_type:%s' % node_type)
    nodes = []
    for item in hits:
        if node_property:
            if lowerstr(item[node_property]) == lowerstr(node_value):
                nodes.append(item)
        else:
            for val in item.propertyValues:
                if lowerstr(val) == lowerstr(node_value):
                    nodes.append(item)
    return nodes

#        
#def get_suitable_nodes(node):
#    '''
#    Takes a reference node and returns all nodes that is suitable for a
#    relationship with that node.
#    
#    Returns a dictionary with the suitable nodes in lists separated by 
#    meta_type.
#    '''
#    meta_type = get_node_meta_type(node).lower()
#    
#    # Create and fill the dictionary with all nodes
#    suitable_types = {'physical': [], 'logical': [], 
#                      'relation': [], 'location': []}
#    for key in suitable_types:
#        meta_node = get_meta_node(key)
#        suitable_types[key] = meta_node.traverse(Outgoing.Contains)
#    # Remove the reference node, can't have relationship with yourself        
#    suitable_types[meta_type].remove(node)
#    # Unreference the types of nodes that are un suitable                  
#    if meta_type == 'location':
#        suitable_types['location'] = []
#        suitable_types['logical'] = []
#    elif meta_type == 'logical':
#        suitable_types['location'] = []
#    elif meta_type == 'relation':
#        suitable_types['relation'] = []
#    return suitable_types
#        
#def make_suitable_relationship(node, other_node, rel_type):
#    '''
#    Makes a relationship from node to other_node depending on which
#    meta_type the nodes sent in are. Returns the relationship or None
#    if no relationship was made.
#    '''
#    meta_type = get_node_meta_type(node)
#    other_meta_type = get_node_meta_type(other_node)
#    rel = None
#    if meta_type == 'location':                # Location
#        if other_meta_type == 'location':
#            rel = node.Has(other_node)
#    elif meta_type == 'logical':               # Logical
#        if other_meta_type == 'logical':
#            rel = node.Depends_on(other_node)
#        elif other_meta_type == 'physical':
#            rel = node.Depends_on(other_node)
#    elif meta_type == 'relation':              # Relation
#        if other_meta_type == 'logical':
#            if rel_type == 'Uses':
#                rel = node.Uses(other_node)
#            elif rel_type == 'Provides':
#                rel = node.Provides(other_node)
#        elif other_meta_type == 'location':
#            rel = node.Responsible_for(other_node)
#        elif other_meta_type == 'physical':
#            if rel_type == 'Owns':
#                rel = node.Owns(other_node)
#            elif rel_type == 'Provides':
#                rel = node.Provides(other_node)
#    elif meta_type == 'physical':              # Physical
#        if other_meta_type == 'physical':
#            if rel_type == 'Has':
#                rel = node.Has(other_node)
#            if rel_type == 'Connected_to':
#                rel = node.Connected_to(other_node)
#        elif other_meta_type == 'location':
#            rel = node.Located_in(other_node)
#    return rel
#        

#
#def get_relationships(n1, n2, rel_type=None):
#    '''
#    Takes a start and an end node with an optional relationship
#    type.
#    Returns the relationsships between the nodes or an empty list.
#    '''
#    rel_list = []
#    for rel in n1.relationships.all():
#        if (rel.start.id == n1.id and rel.end.id == n2.id) or \
#           (rel.start.id == n2.id and rel.end.id == n1.id):
#            if rel_type:
#                if rel.type == rel_type:
#                    rel_list.append(rel)
#            else:
#                rel_list.append(rel)
#    return rel_list
#    
#def relationships_equal(rel, other_rel):
#    '''
#    Takes two relationships and returns True if they have the same start and
#    end node, are of the same type and have the same properties.
#    '''
#    if rel.type == other_rel.type:
#        if rel.start == other_rel.start and rel.end == other_rel.end:
#            if rel.properties == other_rel.properties:
#                return True
#    return False
#
#def update_node_properties(node_id, new_properties):
#    '''
#    Take a node and a dictionary of properties. Updates the
#    node and returns it.
#    '''
#    node = get_node_by_id(node_id)
#    # We might want to do a better check of the data...
#    for key, value in new_properties.items():
#        fixed_key = key.replace(' ','_').lower() # No spaces or caps
#        if value:
#            try:
#                # Handle string representations of lists and booleans
#                node[fixed_key] = json.loads(value)
#            except ValueError:
#                node[fixed_key] = normalize_whitespace(value)
#        elif fixed_key in node.properties:
#            del node[fixed_key]
#    return node
#
#def update_relationship_properties(node_id, rel_id, new_properties):
#    '''
#    Updates the properties of a relationship with the supplied dictionary.
#    '''
#    node = get_node_by_id(node_id)
#    rel = get_relationship_by_id(rel_id, node)
#    for key, value in new_properties.items():
#        fixed_key = key.replace(' ','_').lower() # No spaces or caps
#        if value:
#            rel[fixed_key] = normalize_whitespace(value)
#        elif fixed_key in rel.properties:
#            del rel[fixed_key]
#    return rel
#
#def merge_properties(node_id, prop_name, new_props):
#    '''
#    Tries to figure out which type of property value that should be merged and
#    invoke the right function.
#    Returns True if the merge was successfull otherwise False.
#    '''
#    node = get_node_by_id(node_id)
#    existing_properties = node.get(prop_name, None)
#    if not existing_properties: # A new node without existing properties
#        node[prop_name] = new_props
#        return True
#    else:
#        if type(existing_properties) is int:
#            return False # Not implemented yet
#        elif type(existing_properties) is str:
#            return False # Not implemented yet
#        elif type(existing_properties) is list:
#            merged_props = merge_properties_list(prop_name, new_props,
#                                                        existing_properties)
#        elif type(existing_properties) is dict:
#            return False # Not implemented yet
#        else:
#            return False
#    if merged_props:
#        node[prop_name] = merged_props
#    else:
#        return False
#
#def merge_properties_list(prop_name, new_prop_list, existing_prop_list):
#    '''
#    Takes the name of a property, a list of new property values and the existing
#    node values.
#    Returns the merged properties.
#    '''
#    for item in new_prop_list:
#        if item not in existing_prop_list:
#            existing_prop_list.append(item)
#    return existing_prop_list
#
# Indexes
def search_index_name():
    '''
    Set the name of the index that is used for autocomplete and search in the
    gui.
    '''
    return 'search'
  
def get_node_index(db, index_name):
    '''
    Returns the index with the supplied name. Creates a new index if it does
    not exist.
    '''
    try:
        index = db.nodes.indexes.get(index_name)
    except ValueError:
        with db.transaction:
            index = db.nodes.indexes.create(index_name, type="fulltext", 
                                            provider="lucene")
    return index
    
def get_relationship_index(db, index_name):
    '''
    Returns the index with the supplied name. Creates a new index if it does
    not exist.
    '''
    try:
        index = db.relationships.indexes.get(index_name)
    except ValueError:
        with db.transaction:
            index = db.relationships.indexes.create(index_name, type="fulltext", 
                                            provider="lucene")
    return index

def add_index_item(db, index, item, key):
    '''
    Adds the provided node to the index if the property/key exists and is not
    None. Also adds the node to the index key "all".
    '''
    value = item.getProperty(key, None)
    if value:
        with db.transaction:
            index[key][value] = item
            index['all'][value] = item
        return True
    return False

def del_index_item(db, index, item, key=None):
    '''
    Removes the node from the index. If key is not None, only the indexed
    node[key] will be removed.
    '''
    with db.transaction:
        if key:
            del index[key][item]
        else:
            del index[item]
    return True

# Tests
def test_db_setup(db):
    print 'Testing read and write for Neo4j REST database at %s.' % db.getStoreDir()
    print 'The next two lines should match.'
    print 'Name: root. Node Type: meta. Node ID: 0.'
    with db.transaction:
        n = get_node_by_id(db, '0')
        n['name'] = 'root'
        n['node_type'] = 'meta'
        print 'Name: %s. Node Type: %s. Node ID: %d.' % (n['name'], 
                                                        n['node_type'], n.id)
