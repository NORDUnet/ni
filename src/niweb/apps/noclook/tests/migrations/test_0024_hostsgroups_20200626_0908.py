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

        # This is something that only makes sense for this test:
        # When it's run the target migration is applied two times
        # The first one when it loads the new postgredb
        # The sencond one when on test runtime
        # It seems like after the first one the groups NOC/DEV are deleted
        # on the postgredb but not on neo4j, so at this point if the relational
        # db is empty, we'll empty the node db aswell
        if not NodeHandle.objects.all().exists():
            with nc.graphdb.manager.session as s:
                s.run("MATCH (a:Node) OPTIONAL MATCH (a)-[r]-(b) DELETE a, b, r")

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

            if created:
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
                val = host_node.data.get('responsible_group', None)
                self.assertIsNone(val)
                val = host_node.data.get('support_group', None)
                self.assertIsNone(val)

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


class TestBackwardMigration(MigratorTestCase, NeoTestCase):
    migrate_from = ('noclook', '0024_hostsgroups_20200626_0908')
    migrate_to = ('noclook', '0023_activitylog_context_20200604_1226')

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

        group_type, created = NodeType.objects.get_or_create(
            type='Group', slug='group')
        groups_nhs = NodeHandle.objects.filter(node_type=group_type)

        for host_type_str in host_types:
            # get or create type
            host_type, created = NodeType.objects.get_or_create(
                type=host_type_str,
                slug=slugify(host_type_str)
            )

            responsible_group = random.choice(groups_nhs)
            support_group = random.choice(groups_nhs)

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

            host_node = nc.get_node_model(nc.graphdb.manager, host_nh.handle_id)

            # link groups
            r_gnode = nc.get_node_model(nc.graphdb.manager, responsible_group.handle_id)
            r_gnode.set_takes_responsibility(host_nh.handle_id)

            s_gnode = nc.get_node_model(nc.graphdb.manager, support_group.handle_id)
            s_gnode.set_supports(host_nh.handle_id)

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

                # try to get the old values, assert is not none
                val = host_node.data.get('responsible_group', None)
                self.assertIsNotNone(val)

                val = host_node.data.get('support_group', None)
                self.assertIsNotNone(val)
