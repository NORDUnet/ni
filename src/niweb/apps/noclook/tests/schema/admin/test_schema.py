# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest
from apps.noclook.models import NodeHandleContext
from django.contrib.auth.models import User
from niweb.schema import schema


class GenericUserPermissionTest(Neo4jGraphQLGenericTest):
    def setUp(self, group_dict=None):
        super().setUp(group_dict=group_dict)

        # create another user
        another_user = User.objects.create_user(username='another user',
            email='another@localhost', password='test')
        another_user.is_staff = True
        another_user.save()
        self.another_user = another_user

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
                        'username': 'another user'
                    }}
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
