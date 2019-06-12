# -*- coding: utf-8 -*-
from .neo4j_base import NeoTestCase
from apps.noclook import helpers
from actstream.models import actor_stream
from norduniclient.exceptions import UniqueNodeError


class Neo4jHelpersTest(NeoTestCase):

    def setUp(self):
        super(Neo4jHelpersTest, self).setUp()

        organization = self.create_node('organization1', 'organization', meta='Logical')
        self.organization_node = organization.get_node()

        contact = self.create_node('contact1', 'contact', meta='Relation')
        self.contact_node = contact.get_node()

        contact2 = self.create_node('contact2', 'contact', meta='Relation')
        self.contact2_node = contact2.get_node()

        role = self.create_node('role1', 'role', meta='Logical')
        self.role_node = role.get_node()

    def test_delete_node_utf8(self):
        nh = self.create_node(u'æøå-ftw', 'site')
        node = nh.get_node()

        self.assertEqual(u'æøå-ftw', nh.node_name)
        self.assertEqual(u'æøå-ftw', node.data.get('name'))

        helpers.delete_node(self.user, nh.handle_id)
        activities = actor_stream(self.user)
        self.assertEqual(1, len(activities))
        self.assertEqual(u'Site æøå-ftw', activities[0].data.get('noclook', {}).get('object_name'))

    def test_create_unique_node_handle_case_insensitive(self):
        helpers.create_unique_node_handle(
            self.user,
            'awesomeness',
            'host',
            'Physical')
        with self.assertRaises(UniqueNodeError):
            helpers.create_unique_node_handle(
                self.user,
                'AwesomeNess',
                'host',
                'Physical')

    def test_link_contact_role_for_organization(self):
        thedata = {
            'role_name': 'IT-manager'
        }

        self.assertEqual(len(self.organization_node.relationships), 0)

        contact, role = helpers.link_contact_role_for_organization(self.user, self.organization_node,
                                                                   self.contact_node.handle_id,
                                                                   thedata['role_name']
                                                                   )

        self.assertEqual(role.name, thedata['role_name'])
        self.assertEqual(contact.get_node(), self.organization_node.get_relations().get('Works_for')[0].get('node'))

    def test_create_contact_role_for_organization(self):
        thedata = {
            'contact_name': 'FirstName LastName',
            'role_name': 'IT-manager'
        }

        self.assertEqual(len(self.organization_node.relationships), 0)

        contact, role = helpers.create_contact_role_for_organization(self.user, self.organization_node,
                                                                     thedata['contact_name'],
                                                                     thedata['role_name'],
                                                                     )

        self.assertEqual(contact.get_node(), self.organization_node.get_relations().get('Works_for')[0].get('node'))
        self.assertEqual(contact.get_node().data.get('name'), thedata['contact_name'])
        self.assertEqual(role.name, thedata['role_name'])
