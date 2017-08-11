from .neo4j_base import NeoTestCase
from apps.noclook import helpers
from django.urls import reverse


class VisualizeTest(NeoTestCase):
    """
    Tests the visualize view related functions
    """

    def test_visualize_json(self):
        host_user = self.create_node('AwesomeCo', 'host-user', 'Relation')
        host = self.create_node('sweet-host.nordu.dev', 'host', 'Logical')
        helpers.set_user(self.user, host.get_node(), host_user.handle_id)

        url = reverse('visualize_json', args=[host.handle_id])
        resp = self.client.get(url)

        json = resp.json()
        self.assertEqual(2, len(json['nodes']))
        self.assertEqual(1, len(json['edges']))
        self.assertIn(str(host_user.handle_id), json['edges'].keys())
        self.assertIn(host.node_name, json['nodes'][str(host.handle_id)]['label'])
