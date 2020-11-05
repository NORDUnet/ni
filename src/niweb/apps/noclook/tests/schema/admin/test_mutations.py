# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest
from collections import OrderedDict
from django.contrib.auth.models import User
from niweb.schema import schema
from pprint import pformat

from . import BasicAdminTest

import apps.noclook.vakt.utils as sriutils
import graphene

class AdminMutationsTest(BasicAdminTest):
    def test_set_node_contexts(self):
        # only run mutations if we have set this value
        if not hasattr(self, 'test_type'):
            return

        query_t = """
        mutation{{
          set_nodes_context(input:{{
            contexts: [ {contexts_name} ]
            nodes:[ {nodes_ids} ]
          }}){{
            success
            errors{{
              field
              messages
            }}
            nodes{{
              __typename
              id
              name
            }}
          }}
        }}
        """

        # test fully successful mutation:
        contexts_name = '"{}"'.format(self.network_ctxt.name)
        nodes_ids = []

        for nh in [self.organization, self.host]:
            nodes_ids.append( graphene.relay.Node.to_global_id(
                str(nh.node_type), str(nh.handle_id)) )

        nodes_ids_str = ", ".join([ '"{}"'.format(x) for x in nodes_ids])

        query = query_t.format(
            contexts_name=contexts_name, nodes_ids=nodes_ids_str)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = OrderedDict([('set_nodes_context',
                      {'errors': [],
                       'nodes': [{'__typename': 'Organization',
                                  'id': nodes_ids[0],
                                  'name': 'organization1'},
                                 {'__typename': 'Host',
                                  'id': nodes_ids[1],
                                  'name': 'host1'}],
                       'success': True})])

        self.assert_correct(result, expected)

        # admin test: Has network admin rights and write rights network and
        # contacts so it must be able to do it
        # superadmin: Since the user has every right no problem it should do it
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # test partial successful mutation:
        nodes_ids = []

        for nh in [self.organization, self.host, self.address]:
            nodes_ids.append( graphene.relay.Node.to_global_id(
                str(nh.node_type), str(nh.handle_id)) )

        nodes_ids_str = ", ".join([ '"{}"'.format(x) for x in nodes_ids])

        query = query_t.format(
            contexts_name=contexts_name, nodes_ids=nodes_ids_str)

        if self.test_type == "admin":
            # admin test: It should be able to change only the contexts of
            # the organization and the host, but not the address
            expected = OrderedDict([('set_nodes_context',
              {'errors': [{'field': nodes_ids[2],
                           'messages': ["You don't have write rights for node "
                                        'id {}'.format(nodes_ids[2])]}],
               'nodes': [{'__typename': 'Organization',
                          'id': nodes_ids[0],
                          'name': 'organization1'},
                         {'__typename': 'Host',
                          'id': nodes_ids[1],
                          'name': 'host1'}],
               'success': True})])
        elif self.test_type == "superadmin":
            # superadmin: Since the user has every right no problem it should
            # do it
            expected = OrderedDict([('set_nodes_context',
              {'errors': [],
               'nodes': [{'__typename': 'Organization',
                          'id': nodes_ids[0],
                          'name': 'organization1'},
                         {'__typename': 'Host',
                          'id': nodes_ids[1],
                          'name': 'host1'},
                         {'__typename': 'Address',
                          'id': nodes_ids[2],
                          'name': 'address1'}],
               'success': True})])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        self.assert_correct(result, expected)


    def test_grant_user_permissions(self):
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
                            'username': 'another_user'
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
            {admin}
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
        context_name = net_ctxt.name
        read = str(True).lower()
        list = str(True).lower()
        write = str(True).lower()

        query = query_t.format(
            user_id=another_user_id, context_name=context_name,
            read=read, list=list, write=write, admin=""
        )

        # test vakt functions before
        can_read = sriutils.authorize_read_module(self.another_user, net_ctxt)
        can_list = sriutils.authorize_list_module(self.another_user, net_ctxt)
        can_write = sriutils.authorize_create_resource(self.another_user,
                        net_ctxt)

        self.assertFalse(can_read)
        self.assertFalse(can_list)
        self.assertFalse(can_write)

        # run mutation and check response
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = OrderedDict([
            (
                'grant_user_permission', {
                    'success': True,
                    'errors': None,
                    'user': {
                        'id': str(another_user_id),
                        'user_permissions': {
                            'network': {
                                'admin': False,
                                'list': True,
                                'read': True,
                                'write': True
                            }
                        },
                        'username': 'another_user'
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
        write = str(False).lower()

        query = query_t.format(
            user_id=another_user_id, context_name=context_name,
            read=read, list=list, write=write, admin=""
        )
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = OrderedDict([
            (
                'grant_user_permission', {
                    'success': True,
                    'errors': None,
                    'user': {
                        'id': str(another_user_id),
                        'user_permissions': {
                            'network': {
                                'admin': False,
                                'list': True,
                                'read': True,
                                'write': False
                            }
                        },
                        'username': 'another_user'
                    }
                }
            )
        ])

        # check the user permissions query
        self.assert_correct(result, expected)

        # test vakt functions
        can_write = sriutils.authorize_create_resource(self.another_user,
                        net_ctxt)
        self.assertFalse(can_write)

        # grand admin rights
        admin = "admin: true"
        query = query_t.format(
            user_id=another_user_id, context_name=context_name,
            read=read, list=list, write=write, admin=admin
        )

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        expected = None

        if self.test_type == "admin":
            # if it's superadmin test it should be possible
            expected = OrderedDict([
                ('grant_user_permission', {
                    'success': False,
                    'errors': [{
                        'field': '_', 'messages': \
                            ['Only superadmins can grant admin rights']
                    }],
                    'user': {
                        'id': str(another_user_id),
                        'username': 'another_user',
                        'user_permissions': {
                            'network': {
                                'read': True,
                                'list': True,
                                'write': False,
                                'admin': False
                            }
                        }
                    }
                })])
        elif self.test_type == "superadmin":
            # if it's not check the error
            expected = OrderedDict([
                ('grant_user_permission', {
                    'success': True,
                    'errors': None,
                    'user': {
                        'id': str(another_user_id),
                        'username': 'another_user',
                        'user_permissions': {
                            'network': {
                                'read': True,
                                'list': True,
                                'write': False,
                                'admin': True
                            }}
                        }}
                    )
                ])

        self.assert_correct(result, expected)



class AdminAdminMutationsTestTest(AdminMutationsTest):
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
                'write': False,
            },
        }

        self.test_type = "admin"

        super().setUp(group_dict=group_dict)


class SuperAdminAdminMutationsTestTest(AdminMutationsTest):
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
