# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest
from collections import OrderedDict
from django.contrib.auth.models import User
from niweb.schema import schema
from pprint import pformat

import apps.noclook.vakt.utils as sriutils

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
        # only run mutations if we have set this value
        if not hasattr(self, 'test_type'):
            return

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


        # they must be blank as we didn't set anything yet
        self.assert_correct(result, expected)

        # add read, list and write permissions over our module
        query_t = """
        mutation{{
          grant_user_permission(input:{{
            user_id: {user_id}
            context: "{context_name}"
            read: {read}
            list: {list}
            write: {write}
          }}){{
            success
            errors{{
              field
              messages
            }}
    		user{{
              id
              username
              user_permissions{{
                network{{
                  read
                  list
                  write
                  admin
                }}
              }}
            }}
          }}
        }}
        """

        # check the user permissions query
        net_ctxt = sriutils.get_network_context()
        context_name = net_ctxt.name.lower()
        read = str(True).lower()
        list = str(True).lower()
        write = str(True).lower()

        query = query_t.format(
            user_id=another_user_id, context_name=context_name,
            read=read, list=list, write=write,
        )

        # test vakt functions
        can_read = sriutils.authorize_read_module(self.another_user, net_ctxt)
        can_list = sriutils.authorize_list_module(self.another_user, net_ctxt)
        can_write = sriutils.authorize_create_resource(self.another_user,
                        net_ctxt)

        self.assertFalse(can_read)
        self.assertFalse(can_list)
        self.assertFalse(can_write)

        # before

        # run mutation and check response
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = OrderedDict([
            (
                'grant_user_permission', {
                    'success': True,
                    'errors': None,
                    'user': {
                        'id': '3',
                        'user_permissions': {
                            'network': {
                                'admin': False,
                                'list': True,
                                'read': True,
                                'write': True
                            }
                        },
                        'username': 'another user'
                    }
                }
            )
        ])

        self.assert_correct(result, expected)

        # after
        can_read = sriutils.authorize_read_module(self.another_user, net_ctxt)
        can_list = sriutils.authorize_list_module(self.another_user, net_ctxt)
        can_write = sriutils.authorize_create_resource(self.another_user,
                        net_ctxt)

        self.assertTrue(can_read)
        self.assertTrue(can_list)
        self.assertTrue(can_write)

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
