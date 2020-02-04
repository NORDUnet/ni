# -*- coding: utf-8 -*-
from .neo4j_base import NeoTestCase
from apps.noclook import helpers
from actstream.models import actor_stream
from norduniclient.exceptions import UniqueNodeError
import norduniclient as nc


class Neo4jHelpersTest(NeoTestCase):

    def test_delete_node_utf8(self):
        nh = self.create_node(u'æøå-ftw', 'site')
        node = nh.get_node()

        self.assertEqual(u'æøå-ftw', nh.node_name)
        self.assertEqual(u'æøå-ftw', node.data.get('name'))

        helpers.delete_node(self.user, nh.handle_id)
        activities = actor_stream(self.user)
        self.assertEqual(1, len(activities))
        self.assertEqual(u'Site æøå-ftw', activities[0].data.get('noclook', {}).get('object_name'))

    def test_create_unique_node_handle_case_insensitive(self):
        helpers.create_unique_node_handle(
            self.user,
            'awesomeness',
            'host',
            'Physical')
        with self.assertRaises(UniqueNodeError):
            helpers.create_unique_node_handle(
                self.user,
                'AwesomeNess',
                'host',
                'Physical')

    def test_relationship_to_str_with_id(self):
        nh1 = self.create_node('Router1', 'router')
        router1 = nh1.get_node()

        nh2 = self.create_node('Port1', 'port')
        result = router1.set_has(nh2.handle_id)
        relationship_id = result['Has'][0]['relationship_id']

        out = helpers.relationship_to_str(relationship_id)
        expected = '(Router1 ({a_id}))-[{r_id}:Has]->(Port1 ({b_id}))'.format(a_id=nh1.handle_id, r_id=relationship_id, b_id=nh2.handle_id)
        self.assertEqual(expected, out)

    def test_relationship_to_str_with_model(self):
        nh1 = self.create_node('Router1', 'router')
        router1 = nh1.get_node()

        nh2 = self.create_node('Port1', 'port')
        result = router1.set_has(nh2.handle_id)
        relationship_id = result['Has'][0]['relationship_id']
        rel = nc.get_relationship_model(nc.graphdb.manager, relationship_id)

        out = helpers.relationship_to_str(rel)
        expected = '(Router1 ({a_id}))-[{r_id}:Has]->(Port1 ({b_id}))'.format(a_id=nh1.handle_id, r_id=relationship_id, b_id=nh2.handle_id)
        self.assertEqual(expected, out)
