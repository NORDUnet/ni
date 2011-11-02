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

from norduni_client_exceptions import *
from neo4j import GraphDatabase, Uniqueness, Evaluation, OUTGOING, INCOMING, ANY
from lucenequerybuilder import Q
from django.conf import settings as django_settings
from django.template.defaultfilters import slugify
from datetime import datetime, timedelta
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

def isots_to_dt(item):
    '''
    Returns noclook_last_seen property as a datetime.datetime. If the property
    does not exist we return datetime.datetime.min (0001-01-01 00:00:00).
    '''
    try:
        ts = item['noclook_last_seen']
        #2011-11-01T14:37:13.713434
        dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S.%f')
    except KeyError:
        dt = datetime.min
    return dt

def neo4j_data_age(item):
    '''
    Checks the noclook_last_seen property against datetime.datetime.now() and
    if the differance is greater that django_settings.NEO4J_MAX_DATA_AGE and the
    noclook_auto_manage is true the data is said to be expired.
    Returns noclook_last_seen as a datetime and a "expired" boolean.
    '''
    max_age = timedelta(hours=int(django_settings.NEO4J_MAX_DATA_AGE))
    now = datetime.now()
    last_seen = isots_to_dt(item)
    expired = False
    if (now-last_seen) > max_age and item['noclook_auto_manage']:
        expired = True
    return last_seen, expired

# Core functions
def open_db(uri=NEO4J_URI):
    '''
    Open or create a Neo4j database in the supplied path. As the module
    opens the database located at NEO4J_URI when imported you shouldn't have
    to use this.
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
    return db.nodes.get(int(node_id))
    
def get_all_nodes(db):
    '''
    Returns all nodes in the database in a list. 
    '''
    root = get_root_node(db)
    nodes = []
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
def create_meta_node(db, meta_node_name):
    '''
    Creates a meta node and its' relationship to the root node.
    '''
    if meta_node_name in ['physical', 'logical', 'relation', 'location']:
        with db.transaction:
            meta_node = create_node(db, meta_node_name, 'meta')
            root = get_root_node(db)
            root.Consists_of(meta_node)
        return meta_node
    raise MetaNodeNamingError()
    
def get_meta_node(db, meta_node_name):
    '''
    Will return the meta node requested or create it and return it.
    '''
    root = get_root_node(db)
    if not len(root.relationships):
        # Set root name and node_type as it is the first run
        with neo4jdb.transaction:
            neo4jdb.reference_node['name'] = 'root'
            neo4jdb.reference_node['node_type'] = 'meta'
        return create_meta_node(db, meta_node_name)
    for rel in root.Consists_of.outgoing:
        if rel.end['name'] == meta_node_name.lower():
            return rel.end
    # No meta node found, create one
    meta_node = create_meta_node(db, meta_node_name)
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
    meta_type = None    
    for rel in node.Contains.incoming:
        meta_type = rel.start['name']
    # I only want to do this line but it throws "ValueError: Too many items in 
    # the iterator" when using this function in a traverser.
    #return node.Contains.incoming.single.start['name']
    return meta_type

def get_root_parent(db, node):
    '''
    Takes a node and a string representing the relationship type. Returns the 
    physical nodes' most top parent (not meta node or root node). Returns
    none if no parent was found.
    *** This function does not handle multiple parents. ***
    '''
    # TODO: When traversels support just relationships directions without type 
    # rewrite this function.
    types = {'physical': 'Has', 'logical': 'Depends_on', 'location': 'Has'}
    meta_type = nc.get_node_meta_type(node)
    relationship_type = types[meta_type]
    traverser = db.traversal().relationships(
        relationship_type, INCOMING).traverse(node)
    for n in traverser.nodes:
        if not n == node:
            for rel in n.relationships.incoming:
                if rel.type.name() == relationship_type:
                    break
                return n
    return None
    
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
    q = Q('node_type', '%s' % node_type)
    hits = node_types_index.query('%s' % q)
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

def get_suitable_nodes(db, node):
    '''
    Takes a reference node and returns all nodes that is suitable for a
    relationship with that node.
    
    Returns a dictionary with the suitable nodes in lists separated by 
    meta_type.
    '''
    meta_type = get_node_meta_type(node).lower()
    # Spec which meta types can have a relationship with each other
    if meta_type == 'location':
        suitable_types = ['physical', 'relation', 'location']
    elif meta_type == 'logical':
        suitable_types = ['physical', 'relation', 'logical']
    elif meta_type == 'relation':
        suitable_types = ['physical', 'location', 'logical']
    elif meta_type == 'physical':
        suitable_types = ['physical', 'relation', 'location', 'logical']
    # Get all suitable nodes from graph db
    def suitable_evaluator(path):
    # Filter on the nodes meta type
        if get_node_meta_type(path.end) in suitable_types:
            return Evaluation.INCLUDE_AND_CONTINUE
        return Evaluation.EXCLUDE_AND_CONTINUE
    traverser = db.traversal().evaluator(suitable_evaluator).traverse(node)
    # Create and fill the dictionary with nodes
    node_dict = {'physical': [], 'logical': [], 'relation': [], 'location': []}
    for item in traverser.nodes:
        node_dict[get_node_meta_type(item)].append(item)
    # Remove the reference node, can't have relationship with yourself        
    node_dict[meta_type].remove(node)
    return node_dict

def create_relationship(db, node, other_node, rel_type):
    '''
    Makes a relationship between the two node of the rel_type relationship type.
    To be sure that relationship types are not misspelled or not following
    the database model you should use create_suitable_relationship().
    '''
    with db.transaction:
        return node.relationship.create(rel_type, other_node)


def create_location_relationship(db, location_node, other_node, rel_type):
    '''
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    '''
    if get_node_meta_type(other_node) == 'location' and rel_type == 'Has':
        return create_relationship(db, location_node, other_node, rel_type)
    raise NoRelationshipPossible(location_node, other_node, rel_type)
    
def create_logical_relationship(db, logical_node, other_node, rel_type):
    '''
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    '''
    if rel_type == 'Depends_on':
        other_meta_type = get_node_meta_type(other_node)
        if other_meta_type == 'logical' or other_meta_type == 'physical':
            return create_relationship(db, logical_node, other_node, rel_type)
    raise NoRelationshipPossible(logical_node, other_node, rel_type)
    
def create_relation_relationship(db, relation_node, other_node, rel_type):
    '''
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    '''
    other_meta_type = get_node_meta_type(other_node)
    if other_meta_type == 'logical':
        if rel_type == 'Uses' or rel_type == 'Provides':
            return create_relationship(db, relation_node, other_node, rel_type)
    elif other_meta_type == 'location' and rel_type == 'Responsible_for':
        return create_relationship(db, relation_node, other_node, rel_type)
    elif other_meta_type == 'physical':
        if rel_type == 'Owns' or rel_type == 'Provides':
            return create_relationship(db, relation_node, other_node, rel_type)
    raise NoRelationshipPossible(relation_node, other_node, rel_type)
    
def create_physical_relationship(db, physical_node, other_node, rel_type):
    '''
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    '''
    other_meta_type = get_node_meta_type(other_node)
    if other_meta_type == 'physical':
        if rel_type == 'Has' or rel_type == 'Connected_to':
            return create_relationship(db, physical_node, other_node, rel_type)
    elif other_meta_type == 'location' and rel_type == 'Located_in':
        return create_relationship(db, physical_node, other_node, rel_type)
    raise NoRelationshipPossible(physical_node, other_node, rel_type)

def create_suitable_relationship(db, node, other_node, rel_type):
    '''
    Makes a relationship from node to other_node depending on which
    meta_type the nodes are. Returns the relationship or raises
    NoRelationshipPossible exception.
    '''
    meta_type = get_node_meta_type(node)    
    if meta_type == 'location':
        return create_location_relationship(db, node, other_node, rel_type)
    elif meta_type == 'logical':
        return create_logical_relationship(db, node, other_node, rel_type)
    elif meta_type == 'relation':
        return create_relation_relationship(db, node, other_node, rel_type)
    elif meta_type == 'physical':
        return create_physical_relationship(db, node, other_node, rel_type)
    raise NoRelationshipPossible(node, other_node, rel_type)

def get_relationships(n1, n2, rel_type=None):
    '''
    Takes a start and an end node with an optional relationship
    type.
    Returns the relationsships between the nodes or an empty list.
    '''
    rel_list = []
    for rel in n1.relationships:
        if (rel.start.id == n1.id and rel.end.id == n2.id) or \
           (rel.start.id == n2.id and rel.end.id == n1.id):
            if rel_type:
                if rel.type.name() == rel_type:
                    rel_list.append(rel)
            else:
                rel_list.append(rel)
    return rel_list
    
def relationships_equal(rel1, rel2):
    '''
    Takes two relationships and returns True if they have the same start and
    end node, are of the same type and have the same properties.
    '''
    if rel1.type == rel2.type:
        if rel1.start == rel2.start and rel1.end == rel2.end:
            if rel1.propertyKeys.equals(rel2.propertyKeys):
                if rel1.propertyValues.equals(rel2.propertyValues):
                    return True
    return False

def node2dict(node):
    '''
    Returns the nodes properties as a dictionary.
    '''
    d = []
    for key, value in node.items():
        d[key] = value
    return d

def update_item_properties(db, item, new_properties):
    '''
    Take a node or a relationship and a dictionary of properties. Updates the
    item and returns it.
    '''
    with db.transaction:
    # We might want to do a better check of the data...
        for key, value in new_properties.items():
            fixed_key = key.replace(' ','_').lower() # No spaces or caps
            if value:
                try:
                    # Handle string representations of lists and booleans
                    item[fixed_key] = json.loads(value)
                except ValueError:
                    item[fixed_key] = normalize_whitespace(value)
            elif fixed_key in item.propertyKeys:
                del item[fixed_key]
    return item

def merge_properties(db, node, prop_name, new_props):
    '''
    Tries to figure out which type of property value that should be merged and
    invoke the right function.
    Returns True if the merge was successfull otherwise False.
    '''
    existing_properties = node.getProperty(prop_name, None)
    if not existing_properties: # A node without existing properties
        with db.transaction:
            node[prop_name] = new_props
        return True
    else:
        if type(new_props) is int:
            return False # Not implemented yet
        elif type(new_props) is str:
            return False # Not implemented yet
        elif type(new_props) is list:
            merged_props = merge_properties_list(prop_name, new_props,
                                                        existing_properties)
        elif type(new_props) is dict:
            return False # Not implemented yet
        else:
            return False
    if merged_props:
        with db.transaction:
            node[prop_name] = merged_props
            return True
    else:
        return False

def merge_properties_list(prop_name, new_prop_list, existing_prop_list):
    '''
    Takes the name of a property, a list of new property values and the existing
    node values.
    Returns the merged properties.
    '''
    # Jpype returns lists as jpype._jarray.java.lang.String[].
    existing_prop_list = list(existing_prop_list)
    for item in new_prop_list:
        if item not in existing_prop_list:
            existing_prop_list.append(item)
    return existing_prop_list

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

# Test and setup
def test_db_setup(db_uri=None):
    if db_uri:
        db = open_db(db_uri)
    else:
        db = open_db()
    print 'Testing read and write for Neo4j REST database at %s.' % db.getStoreDir()
    print 'The next two lines should match.'
    print 'Name: root. Node Type: meta. Node ID: 0.'
    with db.transaction:
        n = get_root_node(db)
        n['name'] = 'root'
        n['node_type'] = 'meta'
    print 'Name: %s. Node Type: %s. Node ID: %d.' % (n['name'], n['node_type'], 
                                                     n.id)
    db.shutdown()

def _init_db():
    return open_db()

try:
    neo4jdb = _init_db()
except Exception:
    print '*** WARNING ***'
    print 'Could not load the Neo4j database. Is it already loaded?'
    print 'Use open_db(URI) to open another database.'

def _close_db():
    try:
        neo4jdb.shutdown()
    except NameError:
        print 'Neo4j database already open in another process.'

import atexit
atexit.register(_close_db)

def main():
    test_db_setup()

if __name__ == '__main__':
    main()         
