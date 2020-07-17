# -*- coding: utf-8 -*-
from apps.nerds.lib.consumer_util import get_user
from django_test_migrations.contrib.unittest_case import MigratorTestCase
from django.utils.text import slugify
from apps.noclook.tests.testing import nc
from apps.noclook.tests.neo4j_base import NeoTestCase

try:
    from neo4j.exceptions import CypherError
except ImportError:
    try:
        # pre neo4j 1.4
        from neo4j.v1.exceptions import CypherError
    except ImportError:
        # neo4j 1.1
        from neo4j.v1.api import CypherError

import random

host_types = [
    'Host',
    'Switch',
    'Firewall',
]

class TestMigration(MigratorTestCase, NeoTestCase):
    migrate_from = ('noclook', '0024_hostsgroups_20200626_0908')
    migrate_to = ('noclook', '0025_lastnameoptional_20200701_1015')

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def create_node(self, node_type, node_name, first_name=None, last_name=None):
        contact_nh, created = self.nh_model.objects.get_or_create(
            node_name=node_name, node_type=node_type,
            node_meta_type=nc.META_TYPES[0], # Physical
            creator=self.user,
            modifier=self.user,
        )

        if created:
            try:
                nc.create_node(
                    nc.graphdb.manager,
                    node_name,
                    contact_nh.node_meta_type,
                    node_type.type,
                    contact_nh.handle_id
                )
            except CypherError:
                pass

        contact_node = nc.get_node_model(nc.graphdb.manager, contact_nh.handle_id)

        if first_name:
            contact_node.add_property('first_name', first_name)

        if last_name:
            contact_node.add_property('last_name', last_name)

        return contact_nh, contact_node

    def prepare(self):
        """Create host entities and set random values on responsible/support
        group"""

        User = self.old_state.apps.get_model('auth', 'User')
        NodeType = self.old_state.apps.get_model('noclook', 'NodeType')
        NodeHandle = self.old_state.apps.get_model('noclook', 'NodeHandle')
        self.nh_model = NodeHandle

        username = 'noclook'
        passwd = User.objects.make_random_password(length=30)
        self.user = None

        try:
            self.user = User.objects.get(username=username)
        except:
            self.user = User(username=username, password=passwd).save()

        # create three contacts
        contact_type, created = NodeType.objects.get_or_create(
            type='Contact', slug='contact')

        # one with both first and last name that will be unaffected
        self.create_node(contact_type, "Mary Svensson", "Mary", "Svensson")

        # one with only the node name
        self.create_node(contact_type, "Test")

        # one with node name and last name
        self.create_node(contact_type, "John", None, "John")


    def test_migration(self):
        """Run the test itself."""
        NodeType = self.new_state.apps.get_model('noclook', 'NodeType')
        NodeHandle = self.new_state.apps.get_model('noclook', 'NodeHandle')

        contact_type, created = NodeType.objects.get_or_create(
            type='Contact', slug='contact')

        contact_nhs = NodeHandle.objects.filter(node_type=contact_type)

        for nh in contact_nhs:
            # get their node
            contact_node = nc.get_node_model(nc.graphdb.manager, nh.handle_id)

            # check that node_name and first_name are set
            first_name = contact_node.data.get('first_name', None)
            self.assertIsNotNone(nh.node_name)
            self.assertIsNotNone(first_name)
