from .neo4j_base import NeoTestCase
from apps.noclook.models import NodeHandle, NodeType, UniqueIdGenerator
from apps.noclook import forms, helpers

class CreateOpticalNodeTest(NeoTestCase):
    def setUp(self):
        super(CreateOpticalNodeTest, self).setUp()

        self.node_type='Optical Node'
        self.data = {
            'name': 'test optical node',
            'type': 'ciena6500',
            'operational_state': 'In service',
        }

    def test_plain_creation(self):
        self.data['no_ports'] = True
        resp = self.create(self.data)
        print NodeType.objects.all()

        nh,node = self.get_node(self.data['name'])
        node_data = node.data
        self.assertRedirects(resp, self.get_full_url(nh))
        self.assertEqual("test optical node", node_data['name'])
        self.assertEquals('cienna6500', node_data['type'])
        self.assertEquals('In service', node_data['operational_state'])

    def test_with_ports(self):
        self.data['port_name'] = [
            "Port-1",
            "Port-2",
            "Port-3",
            "Port-4",
            ""
        ]
        self.data['port_type'] = [
            "Fixed",
            "LC",
            "RJ45",
            "E2000",
            "LC"
        ]
        resp = self.create(self.data)

        nh,node = self.get_node(self.data['name'])
        self.assertRedirects(resp, self.get_full_url(nh))

        ports = self.get_ports(node)
        # Missing name should not create a port
        self.assertEqual(4, len(ports))
        
        for i in range(4):
            self.check_port(ports[i], self.data['port_name'][i], self.data['port_type'][i])

    def test_skip_ports(self):
        self.data['port_name'] = [
            "Port-1",
            "Port-2",
        ]
        self.data['port_type'] = [
            "Fixed",
            "LC",
        ]
        self.data['no_ports'] = True
        resp = self.create(self.data)

        nh,node = self.get_node(self.data['name'])
        self.assertRedirects(resp, self.get_full_url(nh))

        ports = self.get_ports(node)
        self.assertEqual(0, len(ports))

    def test_bad_optical_node_type(self):
        self.data['type'] = "NotAType"
        resp =  self.create(self.data)
        self.assertEquals(1, len(resp.context['form'].errors))


    def check_port(self, port, name, port_type):
        pdata = port.get('node').data
        self.assertEqual(name, pdata['name'])
        self.assertEqual(port_type, pdata['port_type'])

