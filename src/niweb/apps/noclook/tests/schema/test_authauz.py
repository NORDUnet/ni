# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, NodeType
from django.template.defaultfilters import slugify
from graphene import relay
from niweb.schema import schema
from pprint import pformat

from .community import Neo4jGraphQLCommunityTest

# we'll use the community test to build a few entities
class Neo4jGraphQLAuthAuzTest(Neo4jGraphQLCommunityTest):
    test_type = 'Organization'

    def check_get_byid(self):
        # get first node and get relay id
        node_type = self.get_nodetype(self.test_type)
        nh = NodeHandle.objects.filter(node_type=node_type).first()
        relay_id = relay.Node.to_global_id(str(node_type),
                                            str(nh.handle_id))
        query = '''
        {{
        	getOrganizationById(id:"{relay_id}"){{
              id
              name
            }}
        }}
        '''.format(relay_id=relay_id)

        expected = None
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '\n{} \n != {}'.format(
                                            pformat(result.data, indent=1),
                                            pformat(expected, indent=1)
                                        )

    def get_nodetype(self, type_name):
        return NodeType.objects.get_or_create(type=type_name, slug=slugify(type_name))[0]

class Neo4jGraphQLAuthenticationTest(Neo4jGraphQLAuthAuzTest):
    def setUp(self):
        super(Neo4jGraphQLAuthenticationTest, self).setUp()

        # do logout
        self.client.logout()

    def test_get_byid(self):
        self.check_get_byid()


class Neo4jGraphQLAuthorizationTest(Neo4jGraphQLAuthAuzTest):
    def setUp(self):
        group_dict = {}
        super(Neo4jGraphQLAuthorizationTest, self).setUp(group_dict=group_dict)

    def test_get_byid(self):
        self.check_get_byid()
