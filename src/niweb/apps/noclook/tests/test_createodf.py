from .neo4j_base import NeoTestCase
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from dynamic_preferences import global_preferences_registry
from apps.noclook.models import NodeHandle, NodeType, UniqueIdGenerator
from apps.noclook import forms, helpers

# We instanciate a manager for our global preferences
global_preferences = global_preferences_registry.manager()


class CreateODFCase(NeoTestCase):
    def setUp(self):
        super(CreateODFCase, self).setUp()
        # Load the default forms
        global_preferences['general__data_domain'] = 'common'
        reload(forms)
        self.node_type = 'ODF'
        self.data = {
            'name': 'test odf',
            'max_number_of_ports': '48',
        }

    def test_only_ODF_creation(self):
        self.data['no_ports'] = True
        resp = self.create(self.data)
        nh,node = self.get_node(self.data['name'])
        odf_data = node.data

        self.assertRedirects(resp, self.get_full_url(nh.get_absolute_url()))
        self.assertEqual(u'test odf', odf_data['name'])
        self.assertEqual(u'48', odf_data['max_number_of_ports'])
        ports = self.get_ports(node)
        self.assertEqual(0, len(ports))


    def test_ODF_port_creation(self):
        self.data['port_type'] = 'LC'
        resp=self.create(self.data)
        nh,node = self.get_node(self.data['name'])
        
        ports = self.get_ports(node)
        self.assertEqual(48, len(ports))

        port = ports[0].get('node').data
        self.assertEqual('LC', port['port_type'])
        self.assertEqual('1', port['name'])

        port15 = ports[14].get('node').data
        self.assertEqual('LC', port15['port_type'])
        self.assertEqual('15', port15['name'])

        port48 = ports[-1].get('node').data
        self.assertEqual('LC', port48['port_type'])
        self.assertEqual('48', port48['name'])

    def test_ODF_port_bundle(self):
        self.data['bundled']=True
        self.data['max_number_of_ports']=12
        self.create(self.data)

        nh,node = self.get_node(self.data['name'])
        ports = self.get_ports(node)
        
        self.assertEqual(6, len(ports))

        port = ports[0].get('node').data
        self.assertEqual('1+2', port['name'])

        port = ports[-1].get('node').data
        self.assertEqual('11+12', port['name'])

    def test_ODF_port_offset(self):
        self.data['offset'] = 13
        self.data['max_number_of_ports'] = 12
        self.create(self.data)

        nh, node = self.get_node(self.data['name'])
        ports = self.get_ports(node)
        self.assertEqual(12, len(ports))
        
        port = ports[0].get('node').data
        self.assertEqual('13', port['name'])

        port = ports[-1].get('node').data
        self.assertEqual('24', port['name'])

    def test_ODF_port_prefix(self):
        self.data['prefix'] = 'ge-1/0/'
        self.data['max_number_of_ports'] = 12
        self.create(self.data)

        nh, node = self.get_node(self.data['name'])
        ports = self.get_ports(node)
        self.assertEqual(12, len(ports))
        
        port = ports[0].get('node').data
        self.assertEqual('ge-1/0/1', port['name'])

        port = ports[-1].get('node').data
        self.assertEqual('ge-1/0/12', port['name'])


    def test_ODF_port_all(self):
        self.data['prefix'] = 'ge-1/0/'
        self.data['bundled']=True
        self.data['offset']=2
        self.data['max_number_of_ports'] = 12
        self.create(self.data)

        nh, node = self.get_node(self.data['name'])
        ports = self.get_ports(node)
        self.assertEqual(6, len(ports))
        
        port = ports[0].get('node').data
        self.assertEqual('ge-1/0/2+3', port['name'])

        port = ports[-1].get('node').data
        self.assertEqual('ge-1/0/12+13', port['name'])

