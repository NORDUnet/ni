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
        has_relation = relation_name in relations_2
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
        getattr(relation_maker, bind_method_name)(self.user, node_1, node_2)

        # check that the relation exists now
        # on the backend
        relations_1 = getattr(node_1.get_node(), node_1_relfname)()
        has_relation = relation_name in relations_1
        self.assertTrue(has_relation)

        relations_2 = getattr(node_2.get_node(), node_2_relfname)()
        has_relation = relation_name in relations_2
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
    def owns(self, relation_f=None, physical_f=None, type_name=None,
                by_id_query=None, graphql_attr=None, relation_name=None):

        super().relation_test(node_1_f=relation_f, node_2_f=physical_f,
            node_1_relfname="_outgoing", node_2_relfname="_incoming",
            type_name=type_name, by_id_query=by_id_query,
            graphql_attr=graphql_attr, relation_name=relation_name,
            relation_maker=RelationDataRelationMaker(),
            bind_method_name="add_owns")

    def test_owns(self):
        community_generator = CommunityFakeDataGenerator()
        network_generator = NetworkFakeDataGenerator()

        test_types = (
            # Organization
            dict(
                relation_f=community_generator.create_organization,
                physical_f=network_generator.create_port,
                type_name='Organization',
                by_id_query='getOrganizationById',
                graphql_attr='owns',
                relation_name='Owns'
            ),
        )

        for type_kwargs in test_types:
            self.owns(**type_kwargs)


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


class MetaTypesQueriesTest(Neo4jGraphQLGenericTest):
    def test_metatype_list(self):
        ## simple metatype query
        query = '''
        {
          getMetatypes
        }
        '''

        expected = {
            "getMetatypes": [
                "Logical",
                "Relation",
                "Physical",
                "Location"
            ]
        }

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors

        self.assertEqual(result.data, expected)


    def test_metatype_classes(self):
        ## get types for metatype

        query_t = '''
        {{
          getTypesForMetatype(metatype: {metatype_name}){{
            type_name
            connection_name
            byid_name
            all_name
          }}
        }}
        '''

        qlogical = query_t.format(metatype_name='Logical')
        qrelation = query_t.format(metatype_name='Relation')
        qphysical = query_t.format(metatype_name='Physical')
        qlocation = query_t.format(metatype_name='Location')

        queries = [qlogical, qrelation, qphysical, qlocation]

        for query in queries:
            result = schema.execute(query, context=self.context)
            assert not result.errors, result.errors


    def check_metatype_search(self, query_t, search_string, metatype_name, \
            types_string, expected_ids, order):

        order_str = ''
        if order:
            order_str = 'orderBy: {}'.format(order)

        query = query_t.format(
            search_string=search_string,
            metatype_name=metatype_name,
            types_string=types_string,
            orderBy=order_str,
        )

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors

        # check expected
        result_nodes = result.data['{}s'.format(metatype_name)]["edges"]

        for node in result_nodes:
            node = node['node']
            self.assertTrue(node['id'] in expected_ids,
                """{} not in expected {}\nresult_nodes: {}\nfor query: {}"""
                """\nfor types: '{}'"""
                    .format(node, expected_ids, result_nodes, search_string,
                            types_string))


    def test_metatype_connections(self):
        net_generator = NetworkFakeDataGenerator()

        metatype_generators = {
            'logical': {
                "Address": net_generator.create_address,
                "Unit": net_generator.create_unit,
            },
            'relation': {
                "Customer": net_generator.create_customer,
                "Provider": net_generator.create_provider,
            },
            'physical': {
                "Switch": net_generator.create_switch,
                "Router": net_generator.create_router,
            },
            'location': {
                "Room": net_generator.create_room,
                "Rack": net_generator.create_rack,
            },
        }

        query_t = '''
        {{
          {metatype_name}s(
            filter: {{
          	  name_contains: "{search_string}"
          	  type_in: [{types_string}]
            }}
            {orderBy}
          ){{
            edges{{
              node{{
                __typename
                id
                name
              }}
            }}
          }}
        }}
        '''

        test_orders = [None, 'name_ASC', 'name_DESC']

        for order in test_orders:
            for metatype_name, types_generator in metatype_generators.items():
                # create entities
                entities = {}

                idx = 0
                for type_name, generator_f in types_generator.items():
                    entity_name = "Test {} - {}".format(idx, type_name)
                    kwargs = dict(name = entity_name)

                    # generate simple locations
                    if metatype_name == "location":
                        kwargs['add_parent'] = False

                    entity = generator_f(**kwargs)


                    entity_id = relay.Node.to_global_id(str(entity.node_type).\
                                                            replace(' ', ''),
                                                        str(entity.handle_id),)

                    entities[type_name] = {
                        'id': entity_id,
                        'entity': entity,
                    }

                    idx = idx + 1

                # perform tests
                # search: name: "est", type: all: expected both
                search_string = "est"
                types_string = ', ' \
                                .join(
                                    [ '"{}"'.format(x) for x in entities.keys()]
                                )
                expected_ids = [y['id'] for x, y in entities.items()]

                self.check_metatype_search(query_t, search_string, \
                    metatype_name, types_string, expected_ids, order)

                # search: name: "don't", type: all: expected none
                search_string = "don't"
                expected_ids = []

                self.check_metatype_search(query_t, search_string, \
                    metatype_name, types_string, expected_ids, order)

                # search: name: "est", type: none: expected none
                search_string = "est"
                types_string = ''

                self.check_metatype_search(query_t, search_string, \
                    metatype_name, types_string, expected_ids, order)

                # search: name: "don't", type: none: expected none
                search_string = "don't"
                self.check_metatype_search(query_t, search_string, \
                    metatype_name, types_string, expected_ids, order)

                # delete created entities
