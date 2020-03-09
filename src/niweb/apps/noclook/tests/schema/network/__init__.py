# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import apps.noclook.vakt.utils as sriutils

from django.core.management import call_command
from django.db import connection

from apps.noclook import helpers
from apps.noclook.management.commands.datafaker import Command as DFCommand
from apps.noclook.models import NodeHandle, Dropdown, Choice, Role, Group, GroupContextAuthzAction, NodeHandleContext
from apps.noclook.tests.neo4j_base import NeoTestCase

class TestContext():
    def __init__(self, user, *ignore):
        self.user = user

class Neo4jGraphQLNetworkTest(NeoTestCase):
    def setUp(self):
        super(Neo4jGraphQLNetworkTest, self).setUp()
        self.context = TestContext(self.user)

        # create group for read in community context
        self.group_read  = Group( name="Group can read the community context" )
        self.group_read.save()

        # create group for write in community context
        self.group_write = Group( name="Group can write for the community context" )
        self.group_write.save()

        # create group for list in community context
        self.group_list = Group( name="Group can list for the community context" )
        self.group_list.save()

        # add user to this group
        self.group_read.user_set.add(self.user)
        self.group_write.user_set.add(self.user)
        self.group_list.user_set.add(self.user)

        # get read aa
        self.get_read_authaction  = sriutils.get_read_authaction()
        self.get_write_authaction = sriutils.get_write_authaction()
        self.get_list_authaction  = sriutils.get_list_authaction()

        # get network context
        self.network_ctxt = sriutils.get_network_context()

        # add contexts and profiles
        GroupContextAuthzAction(
            group = self.group_read,
            authzprofile = self.get_read_authaction,
            context = self.network_ctxt
        ).save()

        GroupContextAuthzAction(
            group = self.group_write,
            authzprofile = self.get_write_authaction,
            context = self.network_ctxt
        ).save()

        GroupContextAuthzAction(
            group = self.group_list,
            authzprofile = self.get_list_authaction,
            context = self.network_ctxt
        ).save()

        # create nodes
        entity_num = 5

        self.create_organization_nodes(5)
        self.create_equicables_nodes(5)

    def create_organization_nodes(self, entity_num):
        call_command(DFCommand.cmd_name,
            **{
                DFCommand.option_organizations: entity_num,
                'verbosity': 0,
            }
        )

    def create_equicables_nodes(self, entity_num):
        call_command(DFCommand.cmd_name,
            **{
                DFCommand.option_equipment: entity_num,
                'verbosity': 0,
            }
        )

    def tearDown(self):
        super(Neo4jGraphQLNetworkTest, self).tearDown()

        # reset sql database
        NodeHandle.objects.all().delete()

        with connection.cursor() as cursor:
            cursor.execute("ALTER SEQUENCE noclook_nodehandle_handle_id_seq RESTART WITH 1")
