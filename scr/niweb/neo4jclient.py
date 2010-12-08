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

    def get_node_by_id(self, node_id):
        '''
        TODO: try except
        '''
        return self.db.nodes.get(int(node_id))

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

    def delete_node(self, node_id):
        '''
        TODO: try except
        '''
        node = self.get_node_by_id(node_id)
        for rel in node.relationships.all():
            rel.delete()
        node.delete()

    def get_relationships(self, start, end, rel_type=None):
        '''
        Takes a start and an end node with an optional relationship
        type.
        Returns the relationsships found or an empty list.
        '''
        rel_list = []
        for rel in start.relationships.all():
            if rel.start.id == start.id and rel.end.id == end.id:
                if rel_type:
                    if rel.type == rel_type:
                        rel_list.append(rel)
                else:
                    rel_list.append(rel)
        return rel_list


def main():

    def test_db_setup():
        import os
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
        nc = Neo4jClient()
        print "Next line should be 0."
        n = nc.get_node_by_id('0')
        print n.id

    test_db_setup()
    return 0

if __name__ == '__main__':
    main()
