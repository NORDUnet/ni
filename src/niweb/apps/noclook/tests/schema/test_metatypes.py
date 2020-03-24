# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest
from apps.noclook.tests.stressload.data_generator import *

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

        relation_maker.add_part_of(group, physical_node)

        # check that the relation exists now
        # on the backend
        has_relation = 'Part_of' in group.get_node()._outgoing()
        self.assertTrue(has_relation)

        has_relation = 'Part_of' in physical_node.get_node()._incoming()
        self.assertTrue(has_relation)

        # on the graphql api
