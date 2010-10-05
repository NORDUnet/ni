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

    def open_db(self, uri):
        '''
        Open or create a Neo4j database in the supplied path.
        '''
        return client.GraphDatabase(uri)

    def create_node(self, name='', type=''):
        '''
        Creates a node with the mandatory attributes name and type.

        TODO: try except
        '''
        return self.db.node(name = name, type = type)

    def get_node_by_id(self, node_id):
        '''
        TODO: try except
        '''
        return self.db.nodes.get(int(node_id))

def main():

    def test_db_setup():
        import os
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
        nc = Neo4jClient()
        n = nc.get_node_by_id('0')
        print n.id

    test_db_setup()
    return 0

if __name__ == '__main__':
    main()
