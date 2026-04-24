from .neo4j_base import NeoTestCase
from operator import itemgetter


class CreateOpticalNodeTest(NeoTestCase):
    def setUp(self):
        super(CreateOpticalNodeTest, self).setUp()

        self.node_type = 'Optical Node'
        self.data = {
            'name': 'test optical node',
            'type': 'ciena6500',
            'operational_state': 'In service',
        }

    def test_plain_creation(self):
        self.data['no_ports'] = True
        resp = self.create(self.data)

        nh, node = self.get_node(self.data['name'])
        node_data = node.data
        self.assertRedirects(resp, self.get_absolute_url(nh))
        self.assertEqual("test optical node", node_data['name'])
        self.assertEqual('ciena6500', node_data['type'])
        self.assertEqual('In service', node_data['operational_state'])

    def test_with_ports(self):
        self.data['prefix'] = 'Port-'
        self.data['port_type'] = 'LC'
        self.data['num_ports'] = '4'
        resp = self.create(self.data)

        nh, node = self.get_node(self.data['name'])
        self.assertRedirects(resp, self.get_absolute_url(nh))

        ports = self.get_ports(node)
        ports = sorted(ports, key=itemgetter('node'))
        # Missing name should not create a port
        self.assertEqual(4, len(ports))

        self.assertEqual('Port-1', ports[0]['node'].data['name'])
        self.assertEqual('LC', ports[0]['node'].data['port_type'])
        self.assertEqual('Port-2', ports[1]['node'].data['name'])
        self.assertEqual('Port-3', ports[2]['node'].data['name'])
        self.assertEqual('Port-4', ports[3]['node'].data['name'])

    def test_skip_ports(self):
        self.data['prefix'] = 'Port-'
        self.data['port_type'] = 'LC'
        self.data['num_ports'] = '4'
        self.data['no_ports'] = True
        resp = self.create(self.data)

        nh, node = self.get_node(self.data['name'])
        self.assertRedirects(resp, self.get_absolute_url(nh))

        ports = self.get_ports(node)
        self.assertEqual(0, len(ports))

    def test_bad_optical_node_type(self):
        self.data['type'] = "NotAType"
        resp = self.create(self.data)
        self.assertEqual(1, len(resp.context['form'].errors))

    def check_port(self, port, name, port_type):
        pdata = port.get('node').data
        self.assertEqual(name, pdata['name'])
        self.assertEqual(port_type, pdata['port_type'])
