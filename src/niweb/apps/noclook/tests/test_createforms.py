# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from dynamic_preferences import global_preferences_registry
from apps.noclook.models import NodeHandle, NodeType
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
        # Set up initial data
        provider_node_type = NodeType.objects.create(type='Provider', slug="provider")
        self.provider = NodeHandle.objects.create(
            node_name='Default Provider',
            node_type=provider_node_type,
            node_meta_type='Relation',
            creator=self.user,
            modifier=self.user,
        )

    def tearDown(self):
        with nc.neo4jdb.transaction as t:
            t.execute("MATCH (a:Node) OPTIONAL MATCH (a)-[r]-(b) DELETE a, b, r").fetchall()
        super(FormTestCase, self).tearDown()

    def get_full_url(self, path):
        return 'http://testserver{}'.format(path)


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
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        data['country'] = 'Sweden'
        self.assertDictContainsSubset(data, nh.get_node().data)

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
        self.assertDictContainsSubset(data, nh.get_node().data)

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
        self.assertDictContainsSubset(data, nh.get_node().data)

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
        self.assertDictContainsSubset(data, nh.get_node().data)
        # TODO: Check relationship


class NordunetNewForms(FormTestCase):

    def setUp(self):
        super(NordunetNewForms, self).setUp()
        # Load the default forms
        global_preferences['general__data_domain'] = 'nordunet'
        reload(forms)

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
        self.assertEqual(NodeType.objects.get(type=node_type).nodehandle_set.count(), 1)
        nh = NodeType.objects.get(type=node_type).nodehandle_set.first()
        self.assertEqual(resp['Location'], self.get_full_url(nh.get_absolute_url()))
        data['name'] = 'SE-TEST SITE'
        data['country'] = 'Sweden'
        self.assertDictContainsSubset(data, nh.get_node().data)
