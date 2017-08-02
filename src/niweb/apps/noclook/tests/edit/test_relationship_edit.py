from ..neo4j_base import NeoTestCase
from django.urls import reverse


class RelationshipEditTest(NeoTestCase):

    def test_update_relationship(self):
        host = self.create_node('nice-host.test.dev', 'host', 'Logical')
        host_service = self.create_node('https', 'host-service', 'Logical')

        host_node = host.get_node()
        result = host_node.set_host_service(host_service.handle_id, '10.0.0.4', '443', 'tcp')
        relationship_id = result.get('Depends_on')[0].get('relationship_id')
        # Setup done

        resp = self.client.post(reverse('relationship_update', args=['host', host.handle_id, relationship_id]),
                                {'public_service': 'true'})

        data = resp.json()
        self.assertEqual(True, data['success'])
        self.assertEqual(True, data['data']['public_service'])
