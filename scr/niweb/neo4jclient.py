#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       neo4jclient.py
#
#       Copyright 2010 Johan Lundberg <lundberg@nordu.net>
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

import client
from django.conf import settings

class Neo4jClient:

    def __init__(self):
        # Open the database defined in settings.py
        self.db = self.open_db(settings.NEO4J_RESOURCE_URI)
        self.client = client
        self.root = self.db.nodes.get(0)
        self.meta_nodes = {} #?
        self.Outgoing = client.Outgoing
        self.Incoming = client.Incoming
        self.Undirected = client.Undirected

    def open_db(self, uri):
        '''
        Open or create a Neo4j database in the supplied path.
        '''
        return client.GraphDatabase(uri)

    def create_node(self, n='', t=''):
        '''
        Creates a node with the mandatory attributes name and type.

        TODO: try except
        '''
        return self.db.node(name = n, type = t)
        
    def get_all_nodes(self):
        '''
        Returns all nodes in the database in a list. 
        
        TODO: try expect
        '''
        nodes = [self.root]
        for meta_node in self.root.traverse():
            nodes.extend(meta_node.traverse())
        return nodes
        
    def get_all_relationships(self):
        '''
        Returns all relationships in the database in a list.
        
        TODO: try except
        '''
        relationships = []
        for node in self.get_all_nodes():
            relationships.extend(node.relationships.all())
        return list(set(relationships))

    def get_node_by_id(self, node_id):
        '''
        TODO: try except
        '''
        return self.db.nodes.get(int(node_id))

    def get_node_meta_type(self, node):
        '''
        Returns the meta type of the supplied node as a string.
        '''
        rel = node.relationships.incoming(types=['Consists_of',
                                                        'Contains'])[0]
        return rel.start['name']

    def get_root_parent(self, node, rel_type):
        '''
        Returns the nodes most top parent (not meta nodes or root node).
        '''
        node_list = node.traverse(types=[rel_type])
        for node in node_list:
            for rel in node.relationships.all():
                if rel.type == 'Contains': # Doesnt all nodes have this rel?
                    return node

        return None

    def get_node_by_value(self, node_value, meta_node_name=None,
                                                    node_property=None):
        '''
        Traverses the meta node, if any, else it traverses all
        available meta nodes and compares the property of the nodes
        with the supplied strings and returns the ones matching.
        '''
        if meta_node_name is not None:
            meta_node = self.get_meta_node(meta_node_name)
            meta_node_list = [meta_node] # It's easy to loop with lists
        else:
            meta_node_list = self.get_all_meta_nodes()

        node_list = []
        for meta_node in meta_node_list:
            for node in meta_node.traverse():
                if node_property is None: # Compare all values
                    for key in node.properties:
                        if node.properties[key].lower() == \
                                                    node_value.lower():
                            node_list.append(node)
                else: # Compare the supplied property value if it exists
                    try:
                        value = node.properties[node_property]
                        if value.lower() == node_value.lower():
                            node_list.append(node)
                    except KeyError:
                        pass

        return node_list

    def get_all_meta_nodes(self):
        '''
        Will return all available meta nodes.
        '''
        rels = self.root.relationships.outgoing(["Consists_of"])
        meta_node_list = []
        for rel in rels:
            meta_node_list.append(rel.end)
        return meta_node_list

    def get_meta_node(self, meta_node_name):
        '''
        Will return the meta node requested or create it and return it.
        '''
        rels = self.root.relationships.outgoing(["Consists_of"])
        for rel in rels:
            if rel.end['name'] == meta_node_name:
                return rel.end
        # No node with requested name found
        n = self.create_node(meta_node_name, 'meta')
        self.root.Consists_of(n)
        return n
        
    def get_suitable_nodes(self, node):
        '''
        Takes a reference node and returns all nodes that is suitable for a
        relationship with that node.
        
        Returns a dictionary with the suitable nodes in separated lists.
        '''
        meta_type = self.get_node_meta_type(node)
        
        # Create and fill the dictionary with all nodes
        suitable_types = {'physical': [], 'logical': [], 
                          'relation': [], 'location': []}
        for key in suitable_types:
            meta_node = self.get_meta_node(key)
            suitable_types[key] = meta_node.traverse(self.Outgoing.Contains)
            
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
        
    def make_suitable_relationship(self, node, other_node, rel_type):
        '''
        Makes a relationship from node to other_node depending on which
        meta_type the nodes sent in are. Returns the relationship or None
        if no relationship was made.
        '''
        meta_type = self.get_node_meta_type(node)
        other_meta_type = self.get_node_meta_type(other_node)
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
        

    def delete_node(self, node_id):
        '''
        TODO: try except
        '''
        node = self.get_node_by_id(node_id)
        for rel in node.relationships.all():
            rel.delete()
        node.delete()
        
    def get_relationship_by_id(self, node, rel_id):
        '''
        Returns the relationship with the supplied id. As there are no
        global collection of relationships you need to supply a node that 
        actually has the wanted relationship.
        
        TODO: Try Except
        '''
        for rel in node.relationships.all():
            if rel.id == int(rel_id):
                return rel
        return False

    def get_relationships(self, n1, n2, rel_type=None):
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

    def update_node_properties(self, node_id, new_properties):
        '''
        Take a node and a dictionary of properties. Updates the
        node and returns it.
        '''
        node = self.get_node_by_id(node_id)
        # We might want to do a better check of the data...
        for key, value in new_properties.items():
            fixed_key = key.replace(' ','_').lower() # No ' ' or caps
            if value:
                node[fixed_key] = value
            elif fixed_key in node.properties:
                del node[fixed_key]
        return node
        
    def update_relationship_properties(self, node, rel_id, new_properties):
        '''
        Updates the properties of a relationship with the supplied dictionary.
        '''
        rel = self.get_relationship_by_id(node, rel_id)
        for key, value in new_properties.items():
            fixed_key = key.replace(' ','_').lower() # No ' ' or caps
            if value:
                rel[fixed_key] = value
            elif fixed_key in rel.properties:
                del rel[fixed_key]
        return rel

def main():

    def test_db_setup():
        import os
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
        nc = Neo4jClient()
        print 'Testing read and write for Neo4j REST database at %s.' \
                                        % settings.NEO4J_RESOURCE_URI
        print 'Next line should be "Root 0".'
        n = nc.get_node_by_id('0')
        n['name'] = 'Root'
        print n['name'], n.id

    test_db_setup()
    return 0

if __name__ == '__main__':
    main()
