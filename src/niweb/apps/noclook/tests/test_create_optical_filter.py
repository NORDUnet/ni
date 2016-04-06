from .neo4j_base import NeoTestCase
from django.contrib.auth.models import User


class CreateOpticalfilterCase(NeoTestCase):
    def setUp(self):
        super(CreateOpticalfilterCase, self).setUp()
        self.node_type = 'Optical Filter'
        self.data = {
            'name': 'test optical filter',
            'max_number_of_ports': '12',
        }

    def test_only_filter_creation(self):
        self.data['no_ports'] = True
        resp = self.create(self.data)

        nh,node = self.get_node(self.data['name'])
        node_data = node.data
        self.assertRedirects(resp, self.get_full_url(nh))
        self.assertEqual("test optical filter", node_data['name'])
        self.assertEqual("12", node_data['max_number_of_ports'])
        ports = self.get_ports(node)
        self.assertEqual(0, len(ports))

    def test_filter_port_creation(self):
        self.data['port_type'] = 'LC'
        resp =  self.create(self.data)
        nh,node = self.get_node(self.data['name'])

        ports = self.get_ports(node)
        self.assertEqual(12, len(ports))

        self.port_test(ports[0].get('node').data, '1', 'LC')
        self.port_test(ports[-1].get('node').data, '12', 'LC')

    def test_filter_port_all(self):
        self.data['bundled']  = True
        self.data['prefix']  = 'ge-1/0/'
        self.data['offset']  = 13
        self.create(self.data)

        nh, node = self.get_node(self.data['name'])
        ports = self.get_ports(node)
        self.assertEqual(6, len(ports))

        self.port_test(ports[0].get('node').data, 'ge-1/0/13+14')
        self.port_test(ports[5].get('node').data, 'ge-1/0/23+24')



    def port_test(self, port, name, port_type=None):
        self.assertEqual(name, port['name'])
        if port_type:
            self.assertEqual(port_type, port['port_type'])

