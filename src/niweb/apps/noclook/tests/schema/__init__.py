# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from django.db import connection

from apps.noclook.models import NodeHandle
from ..neo4j_base import NeoTestCase

class Neo4jGraphQLTest(NeoTestCase):
    def setUp(self):
        super(Neo4jGraphQLTest, self).setUp()

        # create nodes
        organization1 = self.create_node('organization1', 'organization', meta='Logical')
        organization2 = self.create_node('organization2', 'organization', meta='Logical')
        contact1 = self.create_node('contact1', 'contact', meta='Relation')
        contact2 = self.create_node('contact2', 'contact', meta='Relation')
        role1 = self.create_node('role1', 'role', meta='Logical')
        role2 = self.create_node('role2', 'role', meta='Logical')
        group1 = self.create_node('group1', 'group', meta='Logical')
        group2 = self.create_node('group2', 'group', meta='Logical')

        # add some data
        contact1_data = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'name': 'Jane Doe',
        }

        for key, value in contact1_data.items():
            contact1.get_node().add_property(key, value)

        contact2_data = {
            'first_name': 'John',
            'last_name': 'Smith',
            'name': 'John Smith',
        }

        for key, value in contact2_data.items():
            contact2.get_node().add_property(key, value)

        # create relationships
        contact1.get_node().add_role(role1.handle_id)
        contact1.get_node().add_group(group1.handle_id)
        contact1.get_node().add_organization(organization1.handle_id)

        contact2.get_node().add_role(role2.handle_id)
        contact2.get_node().add_group(group2.handle_id)
        contact2.get_node().add_organization(organization2.handle_id)

    def tearDown(self):
        super(Neo4jGraphQLTest, self).tearDown()

        # reset sql database
        NodeHandle.objects.all().delete()

        with connection.cursor() as cursor:
            cursor.execute("ALTER SEQUENCE noclook_nodehandle_handle_id_seq RESTART WITH 1")
