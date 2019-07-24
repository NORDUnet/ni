# -*- coding: utf-8 -*-
from .neo4j_base import NeoTestCase
from apps.noclook import helpers
from apps.noclook.models import Role
from actstream.models import actor_stream
from norduniclient.exceptions import UniqueNodeError


class Neo4jHelpersTest(NeoTestCase):

    def setUp(self):
        super(Neo4jHelpersTest, self).setUp()

        organization = self.create_node('organization1', 'organization', meta='Logical')
        self.organization_node = organization.get_node()

        parent_org = self.create_node('parent organization', 'organization', meta='Logical')
        self.parent_org = parent_org.get_node()

        contact = self.create_node('contact1', 'contact', meta='Relation')
        self.contact_node = contact.get_node()

        contact2 = self.create_node('contact2', 'contact', meta='Relation')
        self.contact2_node = contact2.get_node()

        self.role = Role.objects.get_or_create(name="IT-manager")[0]

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
        self.assertEqual(len(self.organization_node.relationships), 0)

        contact, role = helpers.link_contact_role_for_organization(
            self.user,
            self.organization_node,
            self.contact_node.handle_id,
            self.role
        )

        self.assertEqual(role.name, self.role.name)
        self.assertEqual(
            contact.get_node(),
            self.organization_node.get_relations().get('Works_for')[0].get('node')
        )

    def test_add_parent(self):
        self.assertEqual(self.organization_node.get_relations(), {})
        relationship, created = helpers.set_parent_of(
            self.user, self.organization_node, self.parent_org.handle_id)

        self.assertEqual(
            self.organization_node.get_relations()['Parent_of'][0]['node'],
            self.parent_org
        )

    def test_works_for_role(self):
        self.assertEqual(self.organization_node.get_relations(), {})
        relationship, created = helpers.set_works_for(
            self.user,
            self.contact_node,
            self.organization_node.handle_id,
            self.role.handle_id
        )
        self.assertEqual(
            self.organization_node.get_relations()['Works_for'][0]['relationship_id'],
            relationship.id
        )

        contact = helpers.get_contact_for_orgrole(
            self.organization_node.handle_id,
            self.role
        )

        self.assertEqual(contact.get_node(), self.contact_node)

        helpers.unlink_contact_with_role_from_org(
            self.user,
            self.organization_node,
            self.role
        )
        contact = helpers.get_contact_for_orgrole(
            self.organization_node.handle_id,
            self.role
        )
        self.assertEqual(contact, None)
