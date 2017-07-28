from .neo4j_base import NeoTestCase
from apps.noclook.models import NodeHandle
from apps.noclook.helpers import slug_to_node_type
from django.urls import reverse


class ViewTest(NeoTestCase):

    def test_list_view(self):
        router1 = self.create_node('awesome-router.test.dev', 'router')
        router2 = self.create_node('fine.test.dev', 'router')
        router3 = self.create_node('different-router.test.dev', 'router')

        resp = self.client.get('/router/')
        self.assertContains(resp, router1.node_name)
        self.assertContains(resp, router2.node_name)
        self.assertContains(resp, router3.node_name)
        table_rows = resp.context['table'].rows
        self.assertEqual(table_rows[0].cols[0].get('handle_id'), router1.handle_id)
        self.assertEqual(table_rows[1].cols[0].get('handle_id'), router2.handle_id)
        self.assertEqual(table_rows[2].cols[0].get('handle_id'), router3.handle_id)

    def create_node(self, name, _type, meta='Physical'):
        nt = slug_to_node_type(_type, True)
        return NodeHandle.objects.create(
            node_name='Router1',
            node_type=nt,
            node_meta_type=meta,
            creator=self.user,
            modifier=self.user,
        )
