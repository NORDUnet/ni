# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest
from apps.noclook.tests.stressload.data_generator import *
from collections import OrderedDict
from graphene import relay
from niweb.schema import schema

class Neo4jGraphQLMetatypeTest(Neo4jGraphQLGenericTest):
    pass


class Neo4jGraphQLLogicalTest(Neo4jGraphQLMetatypeTest):
    pass


class Neo4jGraphQLRelationTest(Neo4jGraphQLMetatypeTest):
    pass


class Neo4jGraphQLPhysicalTest(Neo4jGraphQLMetatypeTest):
    pass


class Neo4jGraphQLLocationTest(Neo4jGraphQLMetatypeTest):
    pass


class Neo4jGraphQLGroupTest(Neo4jGraphQLLogicalTest):
    def test_part_of(self):
        community_generator = CommunityFakeDataGenerator()
        network_generator = NetworkFakeDataGenerator()
        relation_maker = LogicalDataRelationMaker()

        group = community_generator.create_group()
        physical_node = network_generator.create_port()

        # check that there's no relation
        # on the backend
        has_relation = 'Part_of' in group.get_node()._outgoing()
        self.assertFalse(has_relation)

        has_relation = 'Part_of' in physical_node.get_node()._incoming()
        self.assertFalse(has_relation)

        # on the graphql api
        group_id = relay.Node.to_global_id(
            'Group', str(group.handle_id))

        query = """
        {{
          getGroupById(id: "{group_id}"){{
            id
            name
            part_of{{
              id
              name
            }}
          }}
        }}
        """.format(group_id=group_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        has_relation = result.data['getGroupById']['part_of'] != None
        self.assertFalse(has_relation)

        # add relation
        relation_maker.add_part_of(group, physical_node)

        # check that the relation exists now
        # on the backend
        has_relation = 'Part_of' in group.get_node()._outgoing()
        self.assertTrue(has_relation)

        has_relation = 'Part_of' in physical_node.get_node()._incoming()
        self.assertTrue(has_relation)

        # on the graphql api
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        has_relation = result.data['getGroupById']['part_of'] != None
        self.assertTrue(has_relation)
