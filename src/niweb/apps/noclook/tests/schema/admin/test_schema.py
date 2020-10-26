# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest
from apps.noclook.models import NodeHandleContext
from django.contrib.auth.models import User
from niweb.schema import schema
from pprint import pformat

from . import BasicAdminTest

import graphene

class GenericUserPermissionTest(BasicAdminTest):
    def test_node_list(self):
        if not hasattr(self, 'test_type'):
            return

        context_t = "contexts: [{context_input}]"
        query_t = """
        {{
          ninodes(filter: {{
            type_in: [{types_str}]
            with_context: {{
              {context}
              exclude: {exclude}
            }}
          }}){{
            edges{{
              node{{
                __typename
                id
                name
              }}
            }}
          }}
        }}
        """
        types_str = ", ".join([
            '"{}"'.format(x) for x in \
                ["Organization", "Host", "Address", "Service", "Cable"]
        ])

        organization_id = graphene.relay.Node.to_global_id(
            str(self.organization.node_type), str(self.organization.handle_id))

        host_id = graphene.relay.Node.to_global_id(
            str(self.host.node_type), str(self.host.handle_id))

        address_id = graphene.relay.Node.to_global_id(
            str(self.address.node_type), str(self.address.handle_id))

        service_id = graphene.relay.Node.to_global_id(
            str(self.service.node_type), str(self.service.handle_id))

        cable_id = graphene.relay.Node.to_global_id(
            str(self.cable.node_type), str(self.cable.handle_id))

        # test empty context (test empty parameter and invalid contexts):
        for context_input in [None, '"Invalid Ctx", "Module"']:
            context_str = ""
            if context_input != None:
                context_str = context_t.format(context_input=context_input)

            # test exclude true: only contexted nodes
            exclude = str(True).lower()

            query = query_t.format(
                types_str=types_str, context=context_str, exclude=exclude,
            )

            result = schema.execute(query, context=self.context)
            assert not result.errors, pformat(result.errors, indent=1)

            expected = {'ninodes':
                            {'edges': [
                                    {'node': {'__typename': 'Organization',
                                    'id': organization_id,
                                    'name': 'organization1'}},
                                    {'node': {'__typename': 'Host',
                                    'id': host_id,
                                    'name': 'host1'}},
                                    {'node': {'__typename': 'Address',
                                    'id': address_id,
                                    'name': 'address1'}}
                                ]
                            }
                        }

            self.assert_correct(result, expected)

            # test exclude false: uncontexted nodes (only for superadmin)
            exclude = str(False).lower()

            query = query_t.format(
                types_str=types_str, context=context_str, exclude=exclude,
            )

            result = schema.execute(query, context=self.context)
            assert not result.errors, pformat(result.errors, indent=1)

            expected = {'ninodes': {'edges': []}}

            if self.test_type == "superadmin":
                expected = {'ninodes': {'edges': [
                                {'node': {'__typename': 'Service',
                                'id': service_id,
                                'name': 'service1'}},
                                {'node': {'__typename': 'Cable',
                                'id': cable_id,
                                'name': 'cable1'}}
                            ]}}

            self.assert_correct(result, expected)

        # test filled context:
        # test exclude true: show nodes out of those contexts
        exclude = str(True).lower()

        # test exclude false: show nodes in of those contexts
        exclude = str(False).lower()

    def test_user_list(self):
        if not hasattr(self, 'test_type'):
            return

        query_t = """
        {{
          users( filter:{{ username_contains: "{name_contains}" }} ){{
            edges{{
              node{{
                id
                username
              }}
            }}
          }}
        }}
        """

        # get both users
        name_contains = "user"
        query = query_t.format(name_contains=name_contains)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = {
            'users': {
                'edges': [
                    {'node': {
                        'id': str(self.user.id),
                        'username': 'test user'
                    }},
                    {'node': {
                        'id': str(self.another_user.id),
                        'username': 'another_user'
                    }},
                ]
            }
        }

        self.assert_correct(result, expected)

        # get only one
        name_contains = "test"
        query = query_t.format(name_contains=name_contains)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = {
            'users': {
                'edges': [
                    {'node': {
                        'id': str(self.user.id),
                        'username': 'test user'
                    }},
                ]
            }
        }

        self.assert_correct(result, expected)


    def test_user_permissions(self):
        # create a simple group with another user
        test_user = self.user
        self.user = self.another_user
        self.group1 = self.create_node('group1', 'group', meta='Logical')
        NodeHandleContext(
            nodehandle=self.group1, context=self.community_ctxt).save()
        self.user = test_user

        query = """
        {
          all_groups{
            name
            modifier{
              user_permissions{
                community{
                  read
                  list
                  write
                }
                network{
                  read
                  list
                  write
                }
                contracts{
                  read
                  list
                  write
                }
              }
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = None

        if hasattr(self, 'test_type'):
            if self.test_type == "user":
                expected = {
                    'all_groups': [{
                        'name': 'group1',
                        'modifier': {
                            'user_permissions': None,
                        }
                    }]
                }
            elif self.test_type == "admin" or self.test_type == "superadmin":
                # check that an admin or superadmin can read permissions of
                # another user

                expected = {
                    'all_groups': [{
                        'name': 'group1',
                        'modifier': {
                            'user_permissions': {
                                'community': {
                                    'read': False,
                                    'list': False,
                                    'write': False,
                                },
                                'network': {
                                    'read': False,
                                    'list': False,
                                    'write': False,
                                },
                                'contracts': {
                                    'read': False,
                                    'list': False,
                                    'write': False,
                                },
                            }
                        }
                    }]
                }

            self.assert_correct(result, expected)


class PlainUserPermissionsTest(GenericUserPermissionTest):
    def setUp(self, group_dict=None):
        group_dict = {
            'community': {
                'admin': False,
                'read': True,
                'list': True,
                'write': True,
            },
            'network': {
                'admin': False,
                'read': True,
                'list': True,
                'write': True,
            },
            'contracts': {
                'admin': False,
                'read': True,
                'list': True,
                'write': True,
            },
        }

        self.test_type = "user"

        super().setUp(group_dict=group_dict)


class AdminUserPermissionsTest(GenericUserPermissionTest):
    def setUp(self, group_dict=None):
        group_dict = {
            'community': {
                'admin': False,
                'read': True,
                'list': True,
                'write': True,
            },
            'network': {
                'admin': True,
                'read': True,
                'list': True,
                'write': True,
            },
            'contracts': {
                'admin': False,
                'read': True,
                'list': True,
                'write': True,
            },
        }

        self.test_type = "admin"

        super().setUp(group_dict=group_dict)


class SuperAdminUserPermissionsTest(GenericUserPermissionTest):
    def setUp(self, group_dict=None):
        group_dict = {
            'community': {
                'admin': True,
                'read': True,
                'list': True,
                'write': True,
            },
            'network': {
                'admin': True,
                'read': True,
                'list': True,
                'write': True,
            },
            'contracts': {
                'admin': True,
                'read': True,
                'list': True,
                'write': True,
            },
        }

        self.test_type = "superadmin"

        super().setUp(group_dict=group_dict)
