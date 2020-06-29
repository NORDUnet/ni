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

class TestForwardMigration(MigratorTestCase, NeoTestCase):
    migrate_from = ('noclook', '0023_activitylog_context_20200604_1226')
    migrate_to = ('noclook', '0024_hostsgroups_20200626_0908')

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def prepare(self):
        """Create host entities and set random values on responsible/support
        group"""

        User = self.old_state.apps.get_model('auth', 'User')
        NodeType = self.old_state.apps.get_model('noclook', 'NodeType')
        NodeHandle = self.old_state.apps.get_model('noclook', 'NodeHandle')
        Dropdown = self.old_state.apps.get_model('noclook', 'Dropdown')
        Choice = self.old_state.apps.get_model('noclook', 'Choice')

        username = 'noclook'
        passwd = User.objects.make_random_password(length=30)
        user = None

        try:
            user = User.objects.get(username=username)
        except:
            user = User(username=username, password=passwd).save()

        for host_type_str in host_types:
            # get or create type
            host_type, created = NodeType.objects.get_or_create(
                type=host_type_str,
                slug=slugify(host_type_str)
            )

            # set old values
            group_dropdwn = Dropdown.objects.get(name="responsible_groups")
            choices = [
                x.value for x in Choice.objects.filter(dropdown=group_dropdwn)
            ]

            responsible_group_val = random.choice(choices)
            support_group_val = random.choice(choices)

            node_name = 'Test {}'.format(host_type_str)

            # create nodehandle and node
            host_nh, created = NodeHandle.objects.get_or_create(
                node_name=node_name, node_type=host_type,
                node_meta_type=nc.META_TYPES[0], # Physical
                creator=user,
                modifier=user,
            )
            try:
                nc.create_node(
                    nc.graphdb.manager,
                    node_name,
                    host_nh.node_meta_type,
                    host_type.type,
                    host_nh.handle_id
                )
            except CypherError:
                pass

            host_node = nc.get_node_model( nc.graphdb.manager, host_nh.handle_id )

            # add properties
            host_node.add_property('responsible_group', responsible_group_val)
            host_node.add_property('support_group', support_group_val)

    def test_migration(self):
        """Run the test itself."""
        NodeType = self.old_state.apps.get_model('noclook', 'NodeType')
        NodeHandle = self.old_state.apps.get_model('noclook', 'NodeHandle')

        # for all types tested
        for host_type_str in host_types:
            host_type = NodeType.objects.get(type=host_type_str)
            host_nhs = NodeHandle.objects.filter(node_type=host_type)

            # for all nhs with this type
            for host_nh in host_nhs:
                host_node = nc.get_node_model(nc.graphdb.manager, host_nh.handle_id)

                # try to get the old values, assert none
                host_node.data.get('responsible_group', None)
                host_node.data.get('support_group', None)

                # check that is linked to a group
                rels = host_node.incoming.get('Takes_responsibility')
                self.assertIsNotNone(rels)
                group_node = rels[0]['node']
                self.assertIsNotNone(group_node)

                # check group name match one of the dropodown's choices
                group_name = group_node.data['name']
                self.assertTrue(
                    NodeHandle.objects.filter(node_name=group_name).exists()
                )

                rels = host_node.incoming.get('Supports')
                self.assertIsNotNone(rels)
                group_node = rels[0]['node']
                self.assertIsNotNone(group_node)

                # check group name match one of the dropodown's choices
                group_name = group_node.data['name']
                self.assertTrue(
                    NodeHandle.objects.filter(node_name=group_name).exists()
                )
