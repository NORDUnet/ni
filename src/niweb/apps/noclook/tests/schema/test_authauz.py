# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, NodeType
from apps.noclook.schema import GraphQLAuthException
from apps.noclook.schema.query import NOCRootQuery
from django.contrib.auth.models import AnonymousUser
from django.template.defaultfilters import slugify
from graphene import relay
from graphql.error.located_error import GraphQLLocatedError
from niweb.schema import schema
from pprint import pformat

from .base import Neo4jGraphQLGenericTest

# we'll use the community test to build a few entities
class Neo4jGraphQLAuthAuzTest(Neo4jGraphQLGenericTest):
    def setUp(self, group_dict=None):
        super(Neo4jGraphQLAuthAuzTest, self).setUp(group_dict=group_dict)
        self.test_user = self.user

    def create_node(self, name, _type, meta='Physical'):
        # in order to perform the node creation with an AnonymousUser
        # we use this simple workaround
        buff_user = self.user
        self.user = self.test_user
        nh = super().create_node(name, _type, meta)
        self.user = buff_user

        return nh


    def loop_get_byid(self):
        for node_type, resolv_dict in NOCRootQuery.by_id_type_resolvers.items():
            graphql_type = resolv_dict['fmt_type_name']
            byid_method = resolv_dict['field_name']

            self.iter_get_byid(
                graphql_type=graphql_type,
                byid_method=byid_method,
                node_type=node_type,
            )

    def check_get_byid(self, graphql_type, byid_method, node_type ,\
                        has_errors=False, expected=None, error_msg=None):
        # get first node and get relay id
        nh = self.create_node("Test node {}".format(graphql_type), node_type.slug)

        relay_id = relay.Node.to_global_id(str(graphql_type),
                                            str(nh.handle_id))
        query = '''
        {{
        	{byid_method}(id:"{relay_id}"){{
              id
              name
            }}
        }}
        '''.format(byid_method=byid_method, relay_id=relay_id)

        if not expected:
            expected = { byid_method: None }

        result = schema.execute(query, context=self.context)

        if not has_errors:
            assert not result.errors, pformat(result.errors, indent=1)
            assert result.data == expected, '\n{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )
        else:
            assert result.errors

            if error_msg:
                error_msg_query = getattr(result.errors[0], 'message')
                assert error_msg_query == error_msg, \
                    '\n{} != {}'.format(
                        error_msg_query,
                        error_msg
                    )

    def run_test_get_byid(self):
        self.loop_get_byid()

class Neo4jGraphQLAuthenticationTest(Neo4jGraphQLAuthAuzTest):
    def setUp(self):
        super(Neo4jGraphQLAuthenticationTest, self).setUp()
        self.user = AnonymousUser()
        self.context.user = self.user

    def iter_get_byid(self, graphql_type, byid_method, node_type):
        error_msg = GraphQLAuthException.default_msg.format('')
        self.check_get_byid(
            graphql_type=graphql_type,
            byid_method=byid_method,
            node_type=node_type,
            has_errors=True,
            error_msg=error_msg
        )

    def test_get_byid(self):
        self.run_test_get_byid()


class Neo4jGraphQLAuthorizationTest(Neo4jGraphQLAuthAuzTest):
    def setUp(self):
        group_dict = {
            'community': {
                'read': False
            }
        }
        super(Neo4jGraphQLAuthorizationTest, self).setUp(group_dict=group_dict)

    def iter_get_byid(self, graphql_type, byid_method, node_type):
        self.check_get_byid(
            graphql_type=graphql_type,
            byid_method=byid_method,
            node_type=node_type
        )

    def test_get_byid(self):
        self.run_test_get_byid()
