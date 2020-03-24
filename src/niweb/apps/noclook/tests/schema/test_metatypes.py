# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest
from apps.noclook.tests.stressload.data_generator import *
from collections import OrderedDict
from graphene import relay
from niweb.schema import schema
from pprint import pformat

class Neo4jGraphQLMetatypeTest(Neo4jGraphQLGenericTest):
    pass


class Neo4jGraphQLLogicalTest(Neo4jGraphQLMetatypeTest):
    def part_of(self, logical_f=None, physical_f=None, type_name=None,
                by_id_query=None, graphql_attr=None, relation_name=None):

        relation_maker = LogicalDataRelationMaker()

        logical_node = logical_f()
        physical_node = physical_f()

        # check that there's no relation
        # on the backend
        has_relation = relation_name in logical_node.get_node()._outgoing()
        self.assertFalse(has_relation)

        has_relation = relation_name in physical_node.get_node()._incoming()
        self.assertFalse(has_relation)

        # on the graphql api
        id = relay.Node.to_global_id(type_name, str(logical_node.handle_id))

        query = """
        {{
          {by_id_query}(id: "{id}"){{
            id
            name
            part_of{{
              id
              name
            }}
          }}
        }}
        """.format(by_id_query=by_id_query, id=id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        has_relation = result.data[by_id_query][graphql_attr] != None
        self.assertFalse(has_relation)

        # add relation
        relation_maker.add_part_of(logical_node, physical_node)

        # check that the relation exists now
        # on the backend
        has_relation = relation_name in logical_node.get_node()._outgoing()
        self.assertTrue(has_relation)

        has_relation = relation_name in physical_node.get_node()._incoming()
        self.assertTrue(has_relation)

        # on the graphql api
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        has_relation = result.data[by_id_query][graphql_attr] != None
        self.assertTrue(has_relation)

    def test_part_of(self):
        community_generator = CommunityFakeDataGenerator()
        network_generator = NetworkFakeDataGenerator()

        test_types = (
            # Group
            dict(
                logical_f=community_generator.create_group,
                physical_f=network_generator.create_port,
                type_name='Group',
                by_id_query='getGroupById',
                graphql_attr='part_of',
                relation_name='Part_of'
            ),
            # Procedure
            dict(
                logical_f=community_generator.create_procedure,
                physical_f=network_generator.create_port,
                type_name='Procedure',
                by_id_query='getProcedureById',
                graphql_attr='part_of',
                relation_name='Part_of'
            ),
        )

        for type_kwargs in test_types:
            self.part_of(**type_kwargs)


class Neo4jGraphQLRelationTest(Neo4jGraphQLMetatypeTest):
    pass


class Neo4jGraphQLPhysicalTest(Neo4jGraphQLMetatypeTest):
    pass


class Neo4jGraphQLLocationTest(Neo4jGraphQLMetatypeTest):
    pass
