# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest
from django.contrib.auth.models import User
from niweb.schema import schema


class GrantUserPermissionTest(Neo4jGraphQLGenericTest):
    def setUp(self, group_dict=None):
        super().setUp(group_dict=group_dict)

        # create another user
        another_user = User.objects.create_user(username='another user',
            email='another@localhost', password='test')
        another_user.is_staff = True
        another_user.save()
        self.another_user = another_user

    def test_mutations(self):
        another_user_id = self.another_user.id

        # first query another_user permissions
        query = """
        {{
          getUserById(ID: {user_id}){{
            id
            username
            user_permissions{{
              community{{
                read
                list
                write
                admin
              }}
              network{{
                read
                list
                write
                admin
              }}
              contracts{{
                read
                list
                write
                admin
              }}
            }}
          }}
        }}
        """.format(user_id=another_user_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = {
                    'getUserById':
                        {
                            'id': str(another_user_id),
                            'user_permissions':
                            {
                                'community': {
                                    'admin': False,
                                    'list': False,
                                    'read': False,
                                    'write': False
                                },
                                'contracts': {
                                    'admin': False,
                                    'list': False,
                                    'read': False,
                                    'write': False
                                },
                                'network': {
                                    'admin': False,
                                    'list': False,
                                    'read': False,
                                    'write': False
                                }
                            },
                            'username': 'another user'
                        }
                    }

        self.assert_correct(result, expected)

        # they must be blank as we didn't set anything yet

        # add read, list and write permissions over our module
        # check the user permissions query
        # test vakt functions

        # revoke write permission
        # check the user permissions query
        # test vakt functions

        # grand admin rights
        # if it's superadmin test it should be possible
        # if it's not check the error


class AdminGrantUserPermissionTest(GrantUserPermissionTest):
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


class SuperAdminGrantUserPermissionTest(GrantUserPermissionTest):
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
