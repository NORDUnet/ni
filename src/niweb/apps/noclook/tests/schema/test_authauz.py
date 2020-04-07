# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, NodeType
from apps.noclook.schema import GraphQLAuthException
from django.contrib.auth.models import AnonymousUser
from django.template.defaultfilters import slugify
from graphene import relay
from graphql.error.located_error import GraphQLLocatedError
from niweb.schema import schema
from pprint import pformat

from .community import Neo4jGraphQLCommunityTest

# we'll use the community test to build a few entities
class Neo4jGraphQLAuthAuzTest(Neo4jGraphQLCommunityTest):
    test_type = 'Organization'
    byid_method = 'getOrganizationById'

    def check_get_byid(self, has_errors=False, expected=None, error_msg=None):
        # get first node and get relay id
        node_type = self.get_nodetype(self.test_type)
        nh = NodeHandle.objects.filter(node_type=node_type).first()
        relay_id = relay.Node.to_global_id(str(node_type),
                                            str(nh.handle_id))
        query = '''
        {{
        	{byid_method}(id:"{relay_id}"){{
              id
              name
            }}
        }}
        '''.format(byid_method=self.byid_method, relay_id=relay_id)

        if not expected:
            expected = { self.byid_method: None }

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

    def get_nodetype(self, type_name):
        return NodeType.objects.get_or_create(type=type_name, slug=slugify(type_name))[0]

class Neo4jGraphQLAuthenticationTest(Neo4jGraphQLAuthAuzTest):
    def setUp(self):
        super(Neo4jGraphQLAuthenticationTest, self).setUp()

        self.user = AnonymousUser()
        self.context.user = self.user

    def test_get_byid(self):
        error_msg = GraphQLAuthException.default_msg.format('')
        self.check_get_byid(has_errors=True, error_msg=error_msg)


class Neo4jGraphQLAuthorizationTest(Neo4jGraphQLAuthAuzTest):
    def setUp(self):
        group_dict = {
            'community': {
                'read': False
            }
        }
        super(Neo4jGraphQLAuthorizationTest, self).setUp(group_dict=group_dict)

    def test_get_byid(self):
        self.check_get_byid()
