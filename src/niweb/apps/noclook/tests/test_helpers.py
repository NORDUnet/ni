# -*- coding: utf-8 -*-
from .neo4j_base import NeoTestCase
from apps.noclook import helpers
from apps.noclook.models import Role
from actstream.models import actor_stream
from norduniclient.exceptions import UniqueNodeError
import norduniclient as nc


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

        group = self.create_node('group1', 'group', meta='Logical')
        self.group_node = group.get_node()

        switch = self.create_node('switch1', 'switch', meta='Physical')
        self.switch_node = switch.get_node()

        site = self.create_node('site1', 'site', meta='Location')
        self.site_node = site.get_node()

        address = self.create_node('address1', 'address', meta='Logical')
        self.address_node = address.get_node()

    def test_delete_node_utf8(self):
        nh = self.create_node(u'æøå-ftw', 'site', meta='Location')
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

    def test_update_contact_organization(self):
        contact, role = helpers.link_contact_role_for_organization(
            self.user,
            self.organization_node,
            self.contact_node.handle_id,
            self.role
        )
        self.assertEqual(len(self.organization_node.relationships), 1)

        anther_role = Role.objects.get_or_create(name="NOC Manager")[0]
        relationship_id = \
            self.organization_node.get_relations()\
                .get('Works_for')[0]['relationship_id']

        contact, role = helpers.link_contact_role_for_organization(
            self.user,
            self.organization_node,
            self.contact_node.handle_id,
            anther_role,
            relationship_id
        )

        self.assertEqual(len(self.organization_node.relationships), 1)
        self.assertEqual(role.name, anther_role.name)

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
            self.role.name
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

    def test_relationship_to_str_with_id(self):
        nh1 = self.create_node('Router1', 'router')
        router1 = nh1.get_node()

        nh2 = self.create_node('Port1', 'port')
        result = router1.set_has(nh2.handle_id)
        relationship_id = result['Has'][0]['relationship_id']

        out = helpers.relationship_to_str(relationship_id)
        expected = '(Router1 ({a_id}))-[{r_id}:Has]->(Port1 ({b_id}))'.format(a_id=nh1.handle_id, r_id=relationship_id, b_id=nh2.handle_id)
        self.assertEqual(expected, out)

    def test_relationship_to_str_with_model(self):
        nh1 = self.create_node('Router1', 'router')
        router1 = nh1.get_node()

        nh2 = self.create_node('Port1', 'port')
        result = router1.set_has(nh2.handle_id)
        relationship_id = result['Has'][0]['relationship_id']
        rel = nc.get_relationship_model(nc.graphdb.manager, relationship_id)

        out = helpers.relationship_to_str(rel)
        expected = '(Router1 ({a_id}))-[{r_id}:Has]->(Port1 ({b_id}))'.format(a_id=nh1.handle_id, r_id=relationship_id, b_id=nh2.handle_id)
        self.assertEqual(expected, out)


    def test_set_supports(self):
        self.assertEqual(self.group_node.get_relations(), {})
        self.assertEqual(self.switch_node.get_relations(), {})

        relationship, created = helpers.set_supports(
            self.user, self.switch_node, self.group_node.handle_id)

        self.assertEqual(
            relationship.start['handle_id'], self.group_node.handle_id)
        self.assertEqual(
            relationship.end['handle_id'], self.switch_node.handle_id)
        self.assertEqual(
            created._properties['handle_id'], self.switch_node.handle_id)


    def test_set_takes_responsibility(self):
        self.assertEqual(self.group_node.get_relations(), {})
        self.assertEqual(self.switch_node.get_relations(), {})

        relationship, created = helpers.set_takes_responsibility(
            self.user, self.switch_node, self.group_node.handle_id)

        self.assertEqual(
            relationship.start['handle_id'], self.group_node.handle_id)
        self.assertEqual(
            relationship.end['handle_id'], self.switch_node.handle_id)
        self.assertEqual(
            created._properties['handle_id'], self.switch_node.handle_id)


    def test_set_address(self):
        self.assertEqual(self.site_node.get_relations(), {})
        self.assertEqual(self.address_node.get_relations(), {})

        site_addresses = self.site_node.get_has_address()
        self.assertEqual(site_addresses, {})

        relationship, created = helpers.set_has_address(
            self.user, self.site_node, self.address_node.handle_id)

        site_addresses = self.site_node.get_has_address()
        self.assertEquals(site_addresses['Has_address'][0]['node'],
                            self.address_node)
