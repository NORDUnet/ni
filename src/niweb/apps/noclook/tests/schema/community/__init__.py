# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import apps.noclook.vakt.utils as sriutils

from django.db import connection

from apps.noclook import helpers
from apps.noclook.models import NodeHandle, Dropdown, Choice, Role, Group, GroupContextAuthzAction, NodeHandleContext
from apps.noclook.tests.neo4j_base import NeoTestCase
from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest

class Neo4jGraphQLTest(Neo4jGraphQLGenericTest):
    def setUp(self):
        super(Neo4jGraphQLTest, self).setUp()

        # create nodes
        self.organization1 = self.create_node('organization1', 'organization', meta='Logical')
        self.organization2 = self.create_node('organization2', 'organization', meta='Logical')
        self.contact1 = self.create_node('contact1', 'contact', meta='Relation')
        self.contact2 = self.create_node('contact2', 'contact', meta='Relation')
        self.group1 = self.create_node('group1', 'group', meta='Logical')
        self.group2 = self.create_node('group2', 'group', meta='Logical')
        self.role1 = Role(name='role1').save()
        self.role2 = Role(name='role2').save()

        # add nodes to the appropiate context
        NodeHandleContext(nodehandle=self.organization1, context=self.community_ctxt).save()
        NodeHandleContext(nodehandle=self.organization2, context=self.community_ctxt).save()
        NodeHandleContext(nodehandle=self.contact1, context=self.community_ctxt).save()
        NodeHandleContext(nodehandle=self.contact2, context=self.community_ctxt).save()
        NodeHandleContext(nodehandle=self.group1, context=self.community_ctxt).save()
        NodeHandleContext(nodehandle=self.group2, context=self.community_ctxt).save()

        # add some data
        contact1_data = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'name': 'Jane Doe',
        }

        for key, value in contact1_data.items():
            self.contact1.get_node().add_property(key, value)

        contact2_data = {
            'first_name': 'John',
            'last_name': 'Smith',
            'name': 'John Smith',
        }

        for key, value in contact2_data.items():
            self.contact2.get_node().add_property(key, value)

        organization1_data = {
            'type': 'university_college',
            'organization_id': 'ORG1',
            'affiliation_customer': True,
        }

        for key, value in organization1_data.items():
            self.organization1.get_node().add_property(key, value)

        organization2_data = {
            'type': 'university_coldep',
            'organization_id': 'ORG2',
            'affiliation_end_customer': True,
        }

        for key, value in organization2_data.items():
            self.organization2.get_node().add_property(key, value)

        # create relationships
        self.contact1.get_node().add_group(self.group1.handle_id)
        self.contact2.get_node().add_group(self.group2.handle_id)

        helpers.link_contact_role_for_organization(
            self.context.user,
            self.organization1.get_node(),
            self.contact1.handle_id,
            self.role1
        )
        helpers.link_contact_role_for_organization(
            self.context.user,
            self.organization2.get_node(),
            self.contact2.handle_id,
            self.role2
        )

        # create dummy dropdown
        dropdown = Dropdown.objects.get_or_create(name='contact_type')[0]
        dropdown.save()
        ch1 = Choice.objects.get_or_create(dropdown=dropdown, name='Person', value='person')[0]
        ch2 = Choice.objects.get_or_create(dropdown=dropdown, name='Group', value='group')[0]
        ch1.save()
        ch2.save()

    def tearDown(self):
        super(Neo4jGraphQLTest, self).tearDown()

        # reset sql database
        NodeHandle.objects.all().delete()

        with connection.cursor() as cursor:
            cursor.execute("ALTER SEQUENCE noclook_nodehandle_handle_id_seq RESTART WITH 1")
