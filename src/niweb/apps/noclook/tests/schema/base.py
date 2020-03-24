# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import apps.noclook.vakt.utils as sriutils

from django.db import connection

from apps.noclook.models import NodeHandle, Group, GroupContextAuthzAction
from apps.noclook.tests.neo4j_base import NeoTestCase
from pprint import pformat

class TestContext():
    def __init__(self, user, *ignore):
        self.user = user

class Neo4jGraphQLGenericTest(NeoTestCase):
    def assert_correct(self, result, expected):
        fmt_str = '{} \n != {}'.format(
                                    pformat(result.data, indent=1),
                                    pformat(expected, indent=1)
                                )
        self.assertEquals(result.data, expected, fmt_str)

    def setUp(self):
        super(Neo4jGraphQLGenericTest, self).setUp()
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
        self.community_ctxt = sriutils.get_community_context()

        # add contexts and profiles for network
        iter_contexts = (
            self.community_ctxt,
            self.network_ctxt,
        )

        group_aaction = (
            (self.group_read, self.get_read_authaction),
            (self.group_write, self.get_write_authaction),
            (self.group_list, self.get_list_authaction),
        )

        for acontext in iter_contexts:
            for group, aaction in group_aaction:
                GroupContextAuthzAction(
                    group = group,
                    authzprofile = aaction,
                    context = acontext
                ).save()

    def tearDown(self):
        super(Neo4jGraphQLGenericTest, self).tearDown()

        # reset sql database
        NodeHandle.objects.all().delete()

        with connection.cursor() as cursor:
            cursor.execute("ALTER SEQUENCE noclook_nodehandle_handle_id_seq RESTART WITH 1")
