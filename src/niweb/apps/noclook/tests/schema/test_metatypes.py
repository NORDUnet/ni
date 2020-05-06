# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest
from apps.noclook.tests.stressload.data_generator import *
from collections import OrderedDict
from graphene import relay
from niweb.schema import schema
from pprint import pformat

class Neo4jGraphQLMetatypeTest(Neo4jGraphQLGenericTest):
    def relation_test(self, node_1_f=None, node_2_f=None, node_1_relfname = None,
                node_2_relfname = None, type_name=None, by_id_query=None,
                graphql_attr=None, relation_name=None, relation_maker=None,
                bind_method_name=None):

        node_1 = node_1_f()
        node_2 = node_2_f()

        # check that there's no relation
        # on the backend
        relations_1 = getattr(node_1.get_node(), node_1_relfname)()
        has_relation = relation_name in relations_1
        self.assertFalse(has_relation)

        relations_2 = getattr(node_2.get_node(), node_2_relfname)()
        has_relation = relation_name in relations_1
        self.assertFalse(has_relation)

        # on the graphql api
        id = relay.Node.to_global_id(type_name, str(node_1.handle_id))

        query = """
        {{
          {by_id_query}(id: "{id}"){{
            id
            name
            {graphql_attr}{{
              id
              name
            }}
          }}
        }}
        """.format(by_id_query=by_id_query, id=id, graphql_attr=graphql_attr)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        has_relation = True if result.data[by_id_query][graphql_attr] else False
        self.assertFalse(has_relation)

        # add relation
        getattr(relation_maker, bind_method_name)(node_1, node_2)

        # check that the relation exists now
        # on the backend
        relations_1 = getattr(node_1.get_node(), node_1_relfname)()
        has_relation = relation_name in relations_1
        self.assertTrue(has_relation)

        relations_2 = getattr(node_2.get_node(), node_2_relfname)()
        has_relation = relation_name in relations_1
        self.assertTrue(has_relation)

        # on the graphql api
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        has_relation = True if result.data[by_id_query][graphql_attr] else False
        self.assertTrue(has_relation)


class Neo4jGraphQLLogicalTest(Neo4jGraphQLMetatypeTest):
    def part_of(self, logical_f=None, physical_f=None, type_name=None,
                by_id_query=None, graphql_attr=None, relation_name=None):

        super().relation_test(node_1_f=logical_f, node_2_f=physical_f,
            node_1_relfname="_outgoing", node_2_relfname="_incoming",
            type_name=type_name, by_id_query=by_id_query,
            graphql_attr=graphql_attr, relation_name=relation_name,
            relation_maker=LogicalDataRelationMaker(),
            bind_method_name="add_part_of")

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
    def parent(self, physical_f=None, type_name=None,
                by_id_query=None, graphql_attr=None, relation_name=None):

        super().relation_test(node_1_f=physical_f, node_2_f=physical_f,
            node_1_relfname="_incoming", node_2_relfname="_outgoing",
            type_name=type_name, by_id_query=by_id_query,
            graphql_attr=graphql_attr, relation_name=relation_name,
            relation_maker=PhysicalDataRelationMaker(),
            bind_method_name="add_parent")

    def test_parent(self):
        network_generator = NetworkFakeDataGenerator()

        test_types = (
            # Port
            dict(
                physical_f=network_generator.create_port,
                type_name='Port',
                by_id_query='getPortById',
                graphql_attr='parent',
                relation_name='Has'
            ),
            # Cable
            dict(
                physical_f=network_generator.create_cable,
                type_name='Cable',
                by_id_query='getCableById',
                graphql_attr='parent',
                relation_name='Has'
            ),
            # Router
            dict(
                physical_f=network_generator.create_router,
                type_name='Router',
                by_id_query='getRouterById',
                graphql_attr='parent',
                relation_name='Has'
            ),
        )

        for type_kwargs in test_types:
            self.parent(**type_kwargs)


class Neo4jGraphQLLocationTest(Neo4jGraphQLMetatypeTest):
    pass
