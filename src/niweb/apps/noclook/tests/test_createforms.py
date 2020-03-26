# -*- coding: utf-8 -*-

try:
    reload
except NameError:
    # Python 3 has reload in importlib
    from importlib import reload
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.utils import six
from dynamic_preferences.registries import global_preferences_registry
from apps.noclook.models import NodeHandle, NodeType, UniqueIdGenerator, ServiceType, ServiceClass
from apps.noclook import forms, helpers
from apps.noclook.tests.testing import nc

__author__ = 'lundberg'

# We instantiate a manager for our global preferences
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
        # Set up initial data
        testing_service_class, created = ServiceClass.objects.get_or_create(name='Testing')
        external_service_type, created = ServiceType.objects.get_or_create(name='External',
                                                                           service_class=testing_service_class)
        external_service_type, created = ServiceType.objects.get_or_create(name='Private Interconnect',
                                                                           service_class=testing_service_class)
        provider_node_type, created = NodeType.objects.get_or_create(type='Provider', slug="provider")
        site_node_type, created = NodeType.objects.get_or_create(type='Site', slug="site")
        optical_node_node_type, created = NodeType.objects.get_or_create(type='Optical Node', slug="optical-node")
        self.provider, created = NodeHandle.objects.get_or_create(
            node_name='Default Provider',
            node_type=provider_node_type,
            node_meta_type='Relation',
            creator=self.user,
            modifier=self.user,
        )
        self.site, created = NodeHandle.objects.get_or_create(
            node_name='Default Site',
            node_type=site_node_type,
            node_meta_type='Location',
            creator=self.user,
            modifier=self.user,
        )
        self.optical_node, created = NodeHandle.objects.get_or_create(
            node_name='Default Optical Node',
            node_type=optical_node_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )

        contact_node_type, created = NodeType.objects.get_or_create(type='Contact', slug="contact")
        organization_node_type, created = NodeType.objects.get_or_create(type='Organization', slug="organization")
        group_node_type, created = NodeType.objects.get_or_create(type='Group', slug="group")

    def tearDown(self):
        with nc.graphdb.manager.session as s:
            s.run("MATCH (a:Node) OPTIONAL MATCH (a)-[r]-(b) DELETE a, b, r")
        super(FormTestCase, self).tearDown()

    def get_full_url(self, path):
        return path


class CommonNewForms(FormTestCase):

    def setUp(self):
        super(CommonNewForms, self).setUp()
        # Load the default forms
        global_preferences['general__data_domain'] = 'common'
        reload(forms)

    def test_NewSiteForm_full(self):
        node_type = 'Site'
        data = {
            'name': 'test site',
            'country_code': 'SE',
            'address': 'Mittiskogen',
            'postarea': 'Skogen',
            'postcode': '12345',
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 2)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.get(node_name='test site')
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        data['country'] = 'Sweden'

        node_data = nh.get_node().data
        for k in data.keys():
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

    def test_NewSiteOwnerForm_full(self):
        node_type = 'Site Owner'
        data = {
            'name': 'test site owner',
            'url': 'http://localhost.se',
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

    def test_NewCustomerForm_full(self):
        node_type = 'Customer'
        data = {
            'name': 'test customer',
            'url': 'http://localhost.se'
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

    def test_NewEndUserForm_full(self):
        node_type = 'End User'
        data = {
            'name': 'test end user',
            'url': 'http://localhost.se'
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

    def test_NewProviderForm_full(self):
        node_type = 'Provider'
        data = {
            'name': 'test provider',
            'url': 'http://localhost.se'
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 2)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.get(node_name='test provider')
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

    def test_NewCableForm_full(self):
        node_type = 'Cable'
        data = {
            'name': 'test cable',
            'cable_type': 'Patch',
            'relationship_provider': self.provider.handle_id
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        del data['relationship_provider']

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

        self.assertEqual(len(nh.get_node().relationships), 1)

    def test_NewRackForm_full(self):
        node_type = 'Rack'
        data = {
            'name': 'test rack',
            'relationship_location': self.site.handle_id
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        del data['relationship_location']

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

        self.assertEqual(len(nh.get_node().relationships), 1)

    def test_NewOdfForm_full(self):
        node_type = 'ODF'
        data = {
            'name': 'test odf',
            'max_number_of_ports': '48'
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

    def test_NewExternalEquipmentForm_full(self):
        node_type = 'External Equipment'
        data = {
            'name': 'test odf',
            'description': 'Very nice external equipment.'
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

    def test_NewPortForm_full(self):
        node_type = 'Port'
        data = {
            'name': 'test port',
            'port_type': 'LC',
            'relationship_parent': self.optical_node.handle_id
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        del data['relationship_parent']

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

        self.assertEqual(len(nh.get_node().relationships), 1)

    def test_NewServiceForm_full_external(self):
        node_type = 'Service'
        data = {
            'name': 'test service',
            'service_type': 'External',
            'operational_state': 'In service',
            'description': 'Pretty good external service',
            'responsible_group': 'DEV',
            'support_group': 'NOC',
            'relationship_provider': self.provider.handle_id
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        del data['relationship_provider']

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

        self.assertEqual(len(nh.get_node().relationships), 1)

    def test_NewOpticalMultiplexSectionForm_full(self):
        node_type = 'Optical Multiplex Section'
        data = {
            'name': 'test optical multiplex section',
            'operational_state': 'In service',
            'description': 'Multiplexing the section!',
            'relationship_provider': self.provider.handle_id,
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        del data['relationship_provider']

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

        self.assertEqual(len(nh.get_node().relationships), 1)

    def test_NewOrganizationForm_full(self):
        node_type = 'Organization'
        data = {
            'name': 'test organization',
            'description': 'SE',
            'organization_id': 'STDH',
            'type': 'university_college',
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        positive_status = True if resp.status_code == 302 or resp.status_code == 200 else False
        self.assertTrue(positive_status)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.get(node_name='test organization')
        self.assertDictContainsSubset(data, nh.get_node().data)

    def test_NewContactForm_full(self):
        node_type = 'Contact'
        country_codes = forms.country_codes()
        if six.PY3:
            country_codes = list(country_codes)

        country_code = country_codes[0]
        data = {
            'first_name': 'Stefan',
            'last_name': 'Listrom',
            'contact_type': 'person',
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        positive_status = True if resp.status_code == 302 or resp.status_code == 200 else False
        self.assertTrue(positive_status)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.get(node_name='Stefan Listrom')
        self.assertDictContainsSubset(data, nh.get_node().data)

    def test_NewProcedureForm_full(self):
        node_type = 'Procedure'
        data = {
            'name': 'Reboot',
            'description': 'Lorem ipsum dolor sit amet',
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.get(node_name='Reboot')
        data['description'] = 'Lorem ipsum dolor sit amet'
        self.assertDictContainsSubset(data, nh.get_node().data)

    def test_NewGroupForm_full(self):
        group_name = 'New users'
        node_type = 'Group'
        data = {
            'name': group_name,
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.get(node_name=group_name)
        data['name'] = group_name
        self.assertDictContainsSubset(data, nh.get_node().data)


class NordunetNewForms(FormTestCase):

    def setUp(self):
        super(NordunetNewForms, self).setUp()
        # Load the default forms
        global_preferences['general__data_domain'] = 'nordunet'
        global_preferences['id_generators__services'] = 'nordunet_service_id'
        reload(forms)
        # Set up a NORDUnet relation
        provider_node_type, created = NodeType.objects.get_or_create(type='Provider', slug="provider")
        self.ndn_provider, created = NodeHandle.objects.get_or_create(
            node_name='NORDUnet',
            node_type=provider_node_type,
            node_meta_type='Relation',
            creator=self.user,
            modifier=self.user,
        )
        # Set up ID generators
        self.service_id_generator, created = UniqueIdGenerator.objects.get_or_create(
            name='nordunet_service_id',
            base_id_length=6,
            zfill=True,
            prefix='SERVICE-',
            creator=self.user
        )
        self.cable_id_generator, created = UniqueIdGenerator.objects.get_or_create(
            name='nordunet_cable_id',
            base_id_length=6,
            zfill=True,
            prefix='CABLE-',
            creator=self.user
        )

    def test_NewSiteForm_full(self):
        node_type = 'Site'
        data = {
            'name': 'test site',
            'country_code': 'SE',
            'address': 'Mittiskogen',
            'postarea': 'Skogen',
            'postcode': '12345'
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 2)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.get(node_name='SE-TEST SITE')
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        data['name'] = 'SE-TEST SITE'
        data['country'] = 'Sweden'

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

    def test_NewCableForm_full(self):
        node_type = 'Cable'
        data = {
            'name': 'test cable',
            'cable_type': 'Patch',
            'relationship_provider': helpers.get_provider_id('NORDUnet')
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        del data['relationship_provider']

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

        self.assertEqual(len(nh.get_node().relationships), 1)

    def test_NewCableForm_generated(self):
        node_type = 'Cable'
        data = {
            'cable_type': 'Patch',
            'relationship_provider': helpers.get_provider_id('NORDUnet')
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        del data['relationship_provider']

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

        self.assertEqual(len(nh.get_node().relationships), 1)
        self.assertEqual(nh.get_node().data['name'], 'CABLE-000001')

    def test_NewServiceForm_full(self):
        node_type = 'Service'
        data = {
            'service_type': 'Private Interconnect',
            'operational_state': 'In service',
            'description': 'Pretty good Interconnect service',
            'responsible_group': 'DEV',
            'support_group': 'NOC',
            'relationship_provider': helpers.get_provider_id('NORDUnet')
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        del data['relationship_provider']

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

        self.assertEqual(len(nh.get_node().relationships), 1)
        self.assertEqual(nh.get_node().data['name'], 'SERVICE-000001')

    def test_NewServiceForm_full_external(self):
        node_type = 'Service'
        data = {
            'name': 'External Test Service',
            'service_type': 'External',
            'operational_state': 'In service',
            'description': 'Pretty good external service',
            'responsible_group': 'DEV',
            'support_group': 'NOC'
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

        self.assertEqual(nh.get_node().data['name'], 'External Test Service')

    def test_NewOpticalLinkForm_full(self):
        node_type = 'Service'
        data = {
            'service_type': 'Private Interconnect',
            'operational_state': 'In service',
            'description': 'Pretty good Interconnect service',
            'responsible_group': 'DEV',
            'support_group': 'NOC',
            'relationship_provider': helpers.get_provider_id('NORDUnet')
        }
        resp = self.client.post('/new/{}/'.format(slugify(node_type)), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        del data['relationship_provider']

        node_data = nh.get_node().data
        for k in data:
            self.assertIn(k, node_data)
            self.assertEqual(data[k], node_data[k])

        self.assertEqual(len(nh.get_node().relationships), 1)
        self.assertEqual(nh.get_node().data['name'], 'SERVICE-000001')
