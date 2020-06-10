# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import apps.noclook.vakt.utils as sriutils

from django.db import connection

from apps.noclook.models import NodeHandle, Group, GroupContextAuthzAction
from apps.noclook.tests.neo4j_base import NeoTestCase
from apps.noclook.tests.testing import nc
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

    def setUp(self, group_dict=None):
        super(Neo4jGraphQLGenericTest, self).setUp()
        self.context = TestContext(self.user)

        # get read aa
        self.get_read_authaction  = sriutils.get_read_authaction()
        self.get_write_authaction = sriutils.get_write_authaction()
        self.get_list_authaction  = sriutils.get_list_authaction()
        self.get_admin_authaction  = sriutils.get_admin_authaction()

        # get contexts
        self.network_ctxt = sriutils.get_network_context()
        self.community_ctxt = sriutils.get_community_context()
        self.contracts_ctxt = sriutils.get_contracts_context()

        # add contexts and profiles for network
        iter_contexts = (
            self.community_ctxt,
            self.network_ctxt,
            self.contracts_ctxt,
        )

        for acontext in iter_contexts:
            # create group for read in community context
            context_name = acontext.name.lower()
            group_read  = Group( name="{} read".format(context_name) )

            # create group for write in community context
            group_write = Group( name="{} write".format(context_name) )

            # create group for list in community context
            group_list  = Group( name="{} list".format(context_name) )

            # create group for admin in community context
            group_admin = Group( name="{} admin".format(context_name) )

            add_read  = False
            add_write = False
            add_list  = False
            add_admin = False

            if group_dict and context_name in group_dict:
                if group_dict[context_name].get('read', False):
                    add_read  = True

                if group_dict[context_name].get('write', False):
                    add_write = True

                if group_dict[context_name].get('list', False):
                    add_list  = True

                if group_dict[context_name].get('admin', False):
                    add_admin  = True

            if not group_dict:
                add_read  = True
                add_write = True
                add_list  = True
                add_admin  = True

            # save and add user to the group
            group_aaction = []

            if add_read:
                group_read.save()
                group_read.user_set.add(self.user)
                group_aaction.append((group_read, self.get_read_authaction))

            if add_write:
                group_write.save()
                group_write.user_set.add(self.user)
                group_aaction.append((group_write, self.get_write_authaction))

            if add_list:
                group_list.save()
                group_list.user_set.add(self.user)
                group_aaction.append((group_list, self.get_list_authaction))

            if add_admin:
                group_admin.save()
                group_admin.user_set.add(self.user)
                group_aaction.append((group_admin, self.get_admin_authaction))

            # add the correct actions fot each group
            for group, aaction in group_aaction:
                GroupContextAuthzAction(
                    group = group,
                    authzprofile = aaction,
                    context = acontext
                ).save()

    def tearDown(self):
        # check that we have the same nodes on neo4j and postgresql
        num_nodes_posgresql = NodeHandle.objects.all().count()
        num_nodes_neo4j = 0

        with nc.graphdb.manager.session as s:
            d = {}
            result = s.run("MATCH (n:Node) RETURN count(n) AS num")
            for record in result:
                for key, value in record.items():
                    d[key] = value

            num_nodes_neo4j = d['num']

        self.assertEqual(num_nodes_posgresql, num_nodes_neo4j)

        super(Neo4jGraphQLGenericTest, self).tearDown()

        # reset sql database
        NodeHandle.objects.all().delete()

        with connection.cursor() as cursor:
            cursor.execute("ALTER SEQUENCE noclook_nodehandle_handle_id_seq RESTART WITH 1")
