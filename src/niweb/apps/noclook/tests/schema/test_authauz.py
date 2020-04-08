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
    create_nodes = 3

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


    def loop_over_types(self, loop_dict=None, iter_func=None):
        for node_type, resolv_dict in loop_dict.items():
            graphql_type = resolv_dict['fmt_type_name']
            api_method = resolv_dict['field_name']

            iter_func(
                graphql_type=graphql_type,
                api_method=api_method,
                node_type=node_type,
            )

    def loop_get_byid(self):
        self.loop_over_types(
            loop_dict=NOCRootQuery.by_id_type_resolvers,
            iter_func=self.iter_get_byid,
        )

    def loop_get_all(self):
        self.loop_over_types(
            loop_dict=NOCRootQuery.all_type_resolvers,
            iter_func=self.iter_get_all,
        )

    def loop_get_connection(self):
        self.loop_over_types(
            loop_dict=NOCRootQuery.connection_type_resolvers,
            iter_func=self.iter_get_connection,
        )

    def check_get_byid(self, graphql_type, api_method, node_type ,\
                        has_errors=False, error_msg=None):
        # get first node and get relay id
        nh = self.create_node("Test node {}".format(graphql_type), node_type.slug)

        relay_id = relay.Node.to_global_id(str(graphql_type),
                                            str(nh.handle_id))
        query = '''
        {{
        	{api_method}(id:"{relay_id}"){{
              id
              name
            }}
        }}
        '''.format(api_method=api_method, relay_id=relay_id)

        expected = { api_method: None }

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

    def check_get_all(self, graphql_type, api_method, node_type ,\
                        has_errors=False, error_msg=None):
        # create 3 nodes for this type
        for i in range(0, self.create_nodes):
            node_name = "Test {} {}".format(graphql_type, i)
            nh = self.create_node(node_name.format(graphql_type), node_type.slug)

        query = """
        {{
          {api_method}{{
            id
            name
          }}
        }}
        """.format(api_method=api_method)

        expected = {
            api_method: []
        }

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

    def check_get_connection(self, graphql_type, api_method, node_type ,\
                        has_errors=False, error_msg=None):
        # create 3 nodes for this type
        for i in range(0, self.create_nodes):
            node_name = "Test {} {}".format(graphql_type, i)
            nh = self.create_node(node_name.format(graphql_type), node_type.slug)

        query = """
        {{
          {api_method}{{
            edges{{
              node{{
                id
                name
              }}
            }}
          }}
        }}
        """.format(api_method=api_method)

        expected = {
            api_method: {
                'edges': []
            }
        }

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

    def run_test_get_all(self):
        self.loop_get_all()

    def run_test_get_connection(self):
        self.loop_get_connection()

    def run_availableDropdowns_choicesForDropdown(self, has_errors=False, \
                                                    error_msg=None):
        dropdown_name = 'email_type'

        query1 = """
        {
          getAvailableDropdowns
        }
        """

        query2 = """
        {{
          getChoicesForDropdown(name: "{dropdown_name}"){{
            name
            value
          }}
        }}
        """

        result = schema.execute(query1, context=self.context)

        if not has_errors:
            # only check for errors
            assert not result.errors, pformat(result.errors, indent=1)

            # get the last one and overwrite
            dropdown_name = result.data['getAvailableDropdowns'][-1]
            query = query2.format(dropdown_name=dropdown_name)

            # run second query, check that there are no errors
            result = schema.execute(query, context=self.context)
            assert not result.errors, pformat(result.errors, indent=1)

            # check that the result isn't empty
            assert result.data['getChoicesForDropdown']

        else:
            # there should be errors here
            assert result.errors

            if error_msg:
                error_msg_query = getattr(result.errors[0], 'message')
                assert error_msg_query == error_msg, \
                    '\n{} != {}'.format(
                        error_msg_query,
                        error_msg
                    )

            # run the other query to check that there's errors too
            query = query2.format(dropdown_name=dropdown_name)
            result = schema.execute(query, context=self.context)

            assert result.errors

            if error_msg:
                error_msg_query = getattr(result.errors[0], 'message')
                assert error_msg_query == error_msg, \
                    '\n{} != {}'.format(
                        error_msg_query,
                        error_msg
                    )

    def run_test_roles(self):
        pass

    def run_test_checkExistentOrganizationId(self):
        pass

    def run_test_availableRoleGroups_rolesFromRoleGroup(self):
        pass


class Neo4jGraphQLAuthenticationTest(Neo4jGraphQLAuthAuzTest):
    def setUp(self):
        super(Neo4jGraphQLAuthenticationTest, self).setUp()
        self.user = AnonymousUser()
        self.context.user = self.user

    def iter_get_byid(self, graphql_type, api_method, node_type):
        error_msg = GraphQLAuthException.default_msg.format('')
        self.check_get_byid(
            graphql_type=graphql_type,
            api_method=api_method,
            node_type=node_type,
            has_errors=True,
            error_msg=error_msg
        )

    def iter_get_all(self, graphql_type, api_method, node_type):
        error_msg = GraphQLAuthException.default_msg.format('')
        self.check_get_all(
            graphql_type=graphql_type,
            api_method=api_method,
            node_type=node_type,
            has_errors=True,
            error_msg=error_msg
        )

    def test_get_byid(self):
        self.run_test_get_byid()

    def test_get_all(self):
        self.run_test_get_all()

    def test_availableDropdowns_choicesForDropdown(self):
        error_msg = GraphQLAuthException.default_msg.format('')
        self.run_availableDropdowns_choicesForDropdown(
            has_errors=True,
            error_msg=error_msg
        )


class Neo4jGraphQLAuthorizationTest(Neo4jGraphQLAuthAuzTest):
    def setUp(self):
        group_dict = {
            'community': {
                'read': False
            }
        }
        super(Neo4jGraphQLAuthorizationTest, self).setUp(group_dict=group_dict)

    def iter_get_byid(self, graphql_type, api_method, node_type):
        self.check_get_byid(
            graphql_type=graphql_type,
            api_method=api_method,
            node_type=node_type
        )

    def iter_get_all(self, graphql_type, api_method, node_type):
        self.check_get_all(
            graphql_type=graphql_type,
            api_method=api_method,
            node_type=node_type
        )

    def iter_get_connection(self, graphql_type, api_method, node_type):
        self.check_get_connection(
            graphql_type=graphql_type,
            api_method=api_method,
            node_type=node_type
        )

    def test_get_byid(self):
        self.run_test_get_byid()

    def test_get_all(self):
        self.run_test_get_all()

    def test_get_connection(self):
        self.run_test_get_connection()

    def test_availableDropdowns_choicesForDropdown(self):
        self.run_availableDropdowns_choicesForDropdown()
