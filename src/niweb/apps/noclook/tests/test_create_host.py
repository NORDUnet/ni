from .neo4j_base import NeoTestCase


class CreateHostView(NeoTestCase):

    def setUp(self):
        super(CreateHostView, self).setUp()
        self.node_type = 'Host'

        self.data = {
            'name': 'awesome.nordu.net',
            'operational_state': 'In service',
        }

    def test_create(self):
        resp = self.create(self.data)

        nh, node = self.get_node('awesome.nordu.net')
        node_data = node.data
        self.assertRedirects(resp, self.get_absolute_url(nh))
        self.assertEqual('awesome.nordu.net', nh.node_name)
        self.assertEqual('awesome.nordu.net', node_data['name'])
        self.assertEqual('In service', node_data['operational_state'])
        self.assertEqual('Host', nh.node_type.type)

    def test_case_insensitive_name_uniqueness(self):
        self.create(self.data)

        self.data['name'] = 'Awesome.NORDU.NET'
        resp = self.create(self.data)
        self.assertEqual(1, len(resp.context['form'].errors))
