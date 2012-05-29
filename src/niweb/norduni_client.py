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
import json
import re

# This started as an extension to the Neo4j REST client made by Versae, continued
# as an extension for the official Neo4j python bindings when they were released
# (Neo4j 1.5, http://docs.neo4j.org/chunked/milestone/python-embedded.html).
#
# The goal is to make it easier to add and retrieve data to a Neo4j database
# according to the NORDUnet Network Inventory data model.
#
# More information about NORDUnet Network Inventory:
# https://portal.nordu.net/display/NI/

# Load Django settings
try:
    from django.conf import settings as django_settings
    NEO4J_URI = django_settings.NEO4J_RESOURCE_URI
except ImportError:
    NEO4J_URI = None
    print 'Starting up without a Django environment.'
    print 'Initial: norduni_client.neo4jdb == None.'
    print 'Use norduni_client.open_db(path_to_directory) to open a database.'
    pass

# Helper functions
def normalize_whitespace(s):
    """
    Removes leading and ending whitespace from a string.
    """
    return ' '.join(s.split())
    
def lowerstr(s):
    """
    Makes everything to a string and tries to make it lower case. Also
    normalizes whitespace.
    """
    return normalize_whitespace(unicode(s).lower())
    
def is_meta_node(node):
    """
    Returns True if the provided node is of node_type == meta.
    """
    if node['node_type'] == 'meta':
        return True
    return False    

# Core functions
def open_db(uri=NEO4J_URI):
    """
    Open or create a Neo4j database in the supplied path. As the module
    opens the database located at NEO4J_URI when imported you shouldn't have
    to use this.
    """
    if uri:
        return GraphDatabase(uri)
        
def upgrade_db(uri=NEO4J_URI):
    """
    Opens the Neo4j database with the option to allow upgrade then closes
    the database and reopen it as neo4jdb.
    """
    if uri:
        db = GraphDatabase(uri, allow_store_upgrade="true")
        db.shutdown()
        print 'Database upgraded!'
    else:
        print 'You did not provide an URI to the database location.'

def create_node(db, n='', t=''):
    """
    Creates a node with the mandatory attributes name and type.
    """
    with db.transaction:
        node = db.node(name=n, node_type=t)
        # Add the nodes name and type to indexes
        i1 = get_node_index(db, search_index_name())
        add_index_item(db, i1, node, 'name')
        i2 = get_node_index(db, 'node_types')
        add_index_item(db, i2, node, 'node_type')
    return node
    
def get_root_node(db):
    """
    Returns the root node, also known as node[0].
    """
    return db.reference_node

def get_node_by_id(db, node_id):
    """
    Returns the node with the supplied id or None if it doesn't exist.
    """
    return db.nodes.get(int(node_id))
    
def get_all_nodes(db):
    """
    Returns all nodes in the database in a list. 
    """
    return [node for node in db.nodes]
    
def get_relationship_by_id(db, rel_id):
    """
    Returns the relationship with the supplied id.
    """
    return db.relationships.get(int(rel_id))
        
def get_all_relationships(db):
    """
    Returns all relationships in the database in a list.
    """
    return [rel for rel in db.relationships]

def delete_node(db, node):
    """
    Deletes the node and all its relationships. Removes the node from all node
    indexes.
    Returns True on success.
    """
    with db.transaction:
        # Delete the nodes all relationships
        for rel in node.relationships:
            delete_relationship(db, rel)
        # Delete the node from all indexes
        for index in get_node_indexes(db):
            del_index_item(db, node, index)
        # Delete the node
        node.delete()
    return True

def delete_relationship(db, rel):
    """
    Deletes the relationship and removes the relationship from all relationship
    indexes.
    Returns True on success.
    """
    with db.transaction:
        # Delete the relationship from all indexes
        for index in get_relationship_indexes(db):
            del_index_item(db, rel, index)
        # Delete relationship
        rel.delete()
    return True    

# NORDUni functions
def create_meta_node(db, meta_node_name):
    """
    Creates a meta node and its' relationship to the root node.
    """
    accepted_names = ['physical', 'logical', 'relation', 'location']
    if meta_node_name in accepted_names:
        with db.transaction:
            meta_node = db.node(name=meta_node_name, node_type='meta')
            root = get_root_node(db)
            root.Consists_of(meta_node)
        return meta_node
    raise MetaNodeNamingError(accepted_names)
    
def get_meta_node(db, meta_node_name):
    """
    Will return the meta node requested or create it and return it.
    """
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
    """
    Will return all meta nodes.
    """
    root = get_root_node(db)
    q = '''
        START root=node(%d)
        MATCH root-[:Consists_of*0..1]->meta_node
        RETURN meta_node
        ''' % root.getId()
    hits = db.query(q)
    return [hit['meta_node'] for hit in hits]
    
def get_node_meta_type(node):
    """
    Returns the meta type of the supplied node as a string.
    """
    try:
        meta_type = node.Contains.incoming.single.start['name']
    except AttributeError:
        raise NoMetaNodeFound(node)
    return meta_type

def get_root_parent(db, node):
    """
    Takes a node and returns the nodes top most parent (not meta node or root node).
    Returns an empty list if no parent was found.

    One gotcha: I choose an arbitrary max depth of 30 to traverse.
    """
    types = {'physical': 'Has', 'logical': 'Depends_on', 'location': 'Has',
             'relation': 'None'} # Relations cant have parent nodes.
    relationship_type = types[nc.get_node_meta_type(node)]
    q = '''
        START node=node(%d)
        MATCH ()-[:Contains]->parent-[:%s*1..30]->node
        RETURN parent
        ''' % (node.getId(), relationship_type)
    hits = nc.neo4jdb.query(q)
    return [hit['parent'] for hit in hits]
    
def get_node_by_value(db, node_value, node_property=None):
    """
    Traverses all nodes and compares the property/properties of the node
    with the supplied string. Returns a list of matching nodes.
    """
    if node_property:
        #q = '''
        #    START node=node(*)
        #    WHERE node.%s! =~ /(?i).*%s.*/
        #    RETURN node
        #    ''' % (node_property, node_value)
        # TODO: Use above when https://github.com/neo4j/community/issues/369 is resolved.
        q = '''
            START node=node(*)
            WHERE has(node.%s)
            RETURN node
            ''' % node_property                                     # Temp
        hits = db.query(q)
        pattern = re.compile('.*%s.*' % node_value, re.IGNORECASE)  # Temp
        for hit in hits:
            if pattern.match(unicode(hit['node'][node_property])):  # Temp
                yield hit['node']
    else:
        pattern = re.compile('.*%s.*' % node_value, re.IGNORECASE)
        for node in nc.get_all_nodes(db):
            for value in node.getPropertyValues():
                if pattern.match(unicode(value)):
                    yield node

def get_indexed_node_by_value(db, node_value, node_type, node_property=None):
    """
    Searches through the node_types index for nodes matching node_type and
    the value or property/value pair. Returns a list of matching nodes.
    """
    if node_property:
        #q = '''
        #    START node=node:node_types(node_type = "%s")
        #    WHERE node.%s! =~ /(?i).*%s.*/
        #    RETURN node
        #    ''' % (node_type, node_property, node_value)
        # TODO: Use above when https://github.com/neo4j/community/issues/369 is resolved.
        q = '''
            START node=node:node_types(node_type = "%s")
            WHERE has(node.%s)
            RETURN node
            ''' % (node_type, node_property)                        # Temp
        hits = db.query(q)
        pattern = re.compile('.*%s.*' % node_value, re.IGNORECASE)  # Temp
        for hit in hits:
            if pattern.match(unicode(hit['node'][node_property])):  # Temp
                yield hit['node']
    else:
        node_types_index = get_node_index(db, 'node_types')
        q = Q('node_type', '%s' % node_type)
        hits = node_types_index.query('%s' % q)
        pattern = re.compile('.*%s.*' % node_value, re.IGNORECASE)
        for hit in hits:
            for value in hit.getPropertyValues():
                if pattern.match(unicode(value)):
                    yield hit

#def get_suitable_nodes(db, node):
#    """
#    Takes a reference node and returns all nodes that is suitable for a
#    relationship with that node.
#
#    Returns a dictionary with the suitable nodes in lists separated by
#    meta_type.
#    """
#    meta_type = get_node_meta_type(node).lower()
#    # Spec which meta types can have a relationship with each other
#    if meta_type == 'location':
#        suitable_types = ['physical', 'relation', 'location']
#    elif meta_type == 'logical':
#        suitable_types = ['physical', 'relation', 'logical']
#    elif meta_type == 'relation':
#        suitable_types = ['physical', 'location', 'logical']
#    elif meta_type == 'physical':
#        suitable_types = ['physical', 'relation', 'location', 'logical']
#    # Get all suitable nodes from graph db
#    def suitable_evaluator(path):
#    # Filter on the nodes meta type
#        if get_node_meta_type(path.end) in suitable_types:
#            return Evaluation.INCLUDE_AND_CONTINUE
#        return Evaluation.EXCLUDE_AND_CONTINUE
#    traverser = db.traversal().evaluator(suitable_evaluator).traverse(node)
#    # Create and fill the dictionary with nodes
#    node_dict = {'physical': [], 'logical': [], 'relation': [], 'location': []}
#    for item in traverser.nodes:
#        node_dict[get_node_meta_type(item)].append(item)
#    # Remove the reference node, can't have relationship with yourself
#    node_dict[meta_type].remove(node)
#    return node_dict

def create_relationship(db, node, other_node, rel_type):
    """
    Makes a relationship between the two node of the rel_type relationship type.
    To be sure that relationship types are not misspelled or not following
    the database model you should use create_suitable_relationship().
    """
    with db.transaction:
        return node.relationship.create(rel_type, other_node)


def create_location_relationship(db, location_node, other_node, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    """
    if get_node_meta_type(other_node) == 'location' and rel_type == 'Has':
        return create_relationship(db, location_node, other_node, rel_type)
    raise NoRelationshipPossible(location_node, other_node, rel_type)
    
def create_logical_relationship(db, logical_node, other_node, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    """
    if rel_type == 'Depends_on':
        other_meta_type = get_node_meta_type(other_node)
        if other_meta_type == 'logical' or other_meta_type == 'physical':
            return create_relationship(db, logical_node, other_node, rel_type)
    raise NoRelationshipPossible(logical_node, other_node, rel_type)
    
def create_relation_relationship(db, relation_node, other_node, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    """
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
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    """
    other_meta_type = get_node_meta_type(other_node)
    if other_meta_type == 'physical':
        if rel_type == 'Has' or rel_type == 'Connected_to':
            return create_relationship(db, physical_node, other_node, rel_type)
    elif other_meta_type == 'location' and rel_type == 'Located_in':
        return create_relationship(db, physical_node, other_node, rel_type)
    raise NoRelationshipPossible(physical_node, other_node, rel_type)

def create_suitable_relationship(db, node, other_node, rel_type):
    """
    Makes a relationship from node to other_node depending on which
    meta_type the nodes are. Returns the relationship or raises
    NoRelationshipPossible exception.
    """
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
    """
    Takes a start and an end node with an optional relationship
    type.
    Returns the relationsships between the nodes or an empty list.
    """
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
    """
    Takes two relationships and returns True if they have the same start and
    end node, are of the same type and have the same properties.
    """
    if rel1.type == rel2.type:
        if rel1.start == rel2.start and rel1.end == rel2.end:
            if rel1.propertyKeys.equals(rel2.propertyKeys):
                if rel1.propertyValues.equals(rel2.propertyValues):
                    return True
    return False

def update_item_properties(db, item, new_properties):
    """
    Take a node or a relationship and a dictionary of properties. Updates the
    item and returns it.
    """
    # We might want to do a better check of the data...
    with db.transaction:
        for key, value in new_properties.items():
            fixed_key = key.replace(' ','_').lower() # No spaces or caps
            if value or value is 0:
                try:
                    # Handle string representations of lists and booleans
                    item[fixed_key] = json.loads(value)
                except ValueError:
                    item[fixed_key] = normalize_whitespace(value)
                except TypeError:
                    item[fixed_key] = value
            elif fixed_key in item.propertyKeys:
                del item[fixed_key]
    return item

def merge_properties(db, node, prop_name, new_props):
    """
    Tries to figure out which type of property value that should be merged and
    invoke the right function.
    Returns True if the merge was successfull otherwise False.
    """
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
    """
    Takes the name of a property, a list of new property values and the existing
    node values.
    Returns the merged properties.
    """
    # Jpype returns lists as jpype._jarray.java.lang.String[].
    existing_prop_list = list(existing_prop_list)
    for item in new_prop_list:
        if item not in existing_prop_list:
            existing_prop_list.append(item)
    return existing_prop_list

# Indexes
def get_node_indexes(db):
    """
    Returns a list of all node indexes in the database.
    """
    return [get_node_index(db, name) for name in db.index().nodeIndexNames()]

def get_relationship_indexes(db):
    """
    Returns a list of all relationship indexes in the database.
    """
    return [get_relationship_index(db, name) 
            for name in db.index().relationshipIndexNames()]

def search_index_name():
    """
    Set the name of the index that is used for autocomplete and search in the
    gui.
    """
    return 'search'
  
def get_node_index(db, index_name):
    """
    Returns the index with the supplied name. Creates a new index if it does
    not exist.
    """
    try:
        index = db.nodes.indexes.get(index_name)
    except ValueError:
        with db.transaction:
            index = db.nodes.indexes.create(index_name, type="fulltext")
    return index
    
def get_relationship_index(db, index_name):
    """
    Returns the index with the supplied name. Creates a new index if it does
    not exist.
    """
    try:
        index = db.relationships.indexes.get(index_name)
    except ValueError:
        with db.transaction:
            index = db.relationships.indexes.create(index_name, type="fulltext")
    return index

def add_index_item(db, index, item, key):
    """
    Adds the provided node to the index if the property/key exists and is not
    None. Also adds the node to the index key "all".
    """
    value = item.getProperty(key, None)
    if value or value == 0:
        with db.transaction:
            index[key][value] = item
            index['all'][value] = item
        return True
    return False

def del_index_item(db, item, index, key=None):
    """
    Removes the node from the index[key]. If key is None all occurences of the
    node in the index will be removed.
    """
    with db.transaction:
        if index and key:
            del index[key][item]
        elif key:
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
except Exception as e:
    print '*** WARNING ***'
    print 'Error: %s' % e
    print 'Could not load the Neo4j database. Is it already loaded?'
    print 'Use open_db(URI) to open another database.'

def _close_db():
    try:
        if neo4jdb:
            neo4jdb.shutdown()
    except NameError:
        print 'Could not shutdown Neo4j database. Is it open in another process?'

import atexit
atexit.register(_close_db)

def main():
    test_db_setup()

if __name__ == '__main__':
    main()         
