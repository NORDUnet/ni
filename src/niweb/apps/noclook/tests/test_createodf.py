from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from dynamic_preferences import global_preferences_registry
from apps.noclook.models import NodeHandle, NodeType, UniqueIdGenerator
from apps.noclook import forms, helpers
import norduniclient as nc

# Use test instance of the neo4j db
nc.neo4jdb = nc.init_db('http://localhost:7475')

# We instanciate a manager for our global preferences
global_preferences = global_preferences_registry.manager()


class FormTestCase(TestCase):

    def setUp(self):
        # Create user
        user = User.objects.create_user(username='test user', email='test@localhost', password='test')
        user.is_staff = True
        user.save()
        self.user = user
        # Set up client
        self.client = Client()
        self.client.login(username='test user', password='test')

    def tearDown(self):
        with nc.neo4jdb.transaction as t:
            t.execute("MATCH (a:Node) OPTIONAL MATCH (a)-[r]-(b) DELETE a, b, r").fetchall()
        super(FormTestCase, self).tearDown()

    def get_full_url(self, path):
        return 'http://testserver{}'.format(path)


class CreateODFCase(FormTestCase):

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
        resp = self.create_odf(self.data)
        nh,node = self.get_odf(self.data['name'])
        odf_data = node.data

        self.assertRedirects(resp, self.get_full_url(nh.get_absolute_url()))
        self.assertEqual(u'test odf', odf_data['name'])
        self.assertEqual(u'48', odf_data['max_number_of_ports'])
        ports = self.get_ports(node)
        self.assertEqual(0, len(ports))


    def test_ODF_port_creation(self):
        self.data['port_type'] = 'LC'
        resp=self.create_odf(self.data)
        nh,node = self.get_odf(self.data['name'])
        
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
        self.create_odf(self.data)

        nh,node = self.get_odf(self.data['name'])
        ports = self.get_ports(node)
        
        self.assertEqual(6, len(ports))

        port = ports[0].get('node').data
        self.assertEqual('1+2', port['name'])

        port = ports[-1].get('node').data
        self.assertEqual('11+12', port['name'])

    def test_ODF_port_offset(self):
        self.data['offset'] = 13
        self.data['max_number_of_ports'] = 12
        self.create_odf(self.data)

        nh, node = self.get_odf(self.data['name'])
        ports = self.get_ports(node)
        self.assertEqual(12, len(ports))
        
        port = ports[0].get('node').data
        self.assertEqual('13', port['name'])

        port = ports[-1].get('node').data
        self.assertEqual('24', port['name'])

    def test_ODF_port_prefix(self):
        self.data['prefix'] = 'ge-1/0/'
        self.data['max_number_of_ports'] = 12
        self.create_odf(self.data)

        nh, node = self.get_odf(self.data['name'])
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
        self.create_odf(self.data)

        nh, node = self.get_odf(self.data['name'])
        ports = self.get_ports(node)
        self.assertEqual(6, len(ports))
        
        port = ports[0].get('node').data
        self.assertEqual('ge-1/0/2+3', port['name'])

        port = ports[-1].get('node').data
        self.assertEqual('ge-1/0/12+13', port['name'])

        


    def get_ports(self, node):
        return node.get_ports().get("Has",[])

    def get_odf(self,name):
        nh = NodeHandle.objects.filter(node_type__type=self.node_type).get(node_name=name)
        node = nh.get_node()
        return nh,node
    def create_odf(self,data):
        url = '/new/{}/'.format(slugify(self.node_type))
        return self.client.post(url, data)


