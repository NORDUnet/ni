# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest
from collections import OrderedDict
from django.contrib.auth.models import User
from niweb.schema import schema
from pprint import pformat

import apps.noclook.vakt.utils as sriutils
import graphene

class BasicAdminTest(Neo4jGraphQLGenericTest):
    def setUp(self, group_dict=None):
        super().setUp(group_dict=group_dict)

        # create another users
        another_user = User.objects.create_user(username='another_user',
            email='another@localhost', password='test')
        another_user.is_staff = True
        another_user.save()
        self.another_user = another_user

        other_user = User.objects.create_user(username='other_user',
            email='other@localhost', password='test')
        other_user.is_staff = True
        other_user.save()
        self.other_user = other_user

        # create some nodes
        self.organization = self.create_node(
                                'organization1', 'organization', meta='Relation')
        self.host = self.create_node(
                                'host1', 'host', meta='Logical')
        self.address = self.create_node(
                                'address1', 'address', meta='Logical')

        # set contexts
        sriutils.set_nodehandle_context(self.community_ctxt, self.organization)
        sriutils.set_nodehandle_context(self.network_ctxt, self.host)
        sriutils.set_nodehandle_context(self.contracts_ctxt, self.address)

        # create nodes without context / module
        self.service = self.create_node(
                                'service1', 'service', meta='Logical')
        self.cable = self.create_node(
                                'cable1', 'cable', meta='Physical')
