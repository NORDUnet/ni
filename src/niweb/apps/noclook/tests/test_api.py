# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from tastypie.test import ResourceTestCase
from tastypie.models import ApiKey
from apps.noclook.models import NodeHandle, NodeType, UniqueIdGenerator
from apps.noclook import helpers
from apps.noclook.tests.testing import nc

__author__ = 'lundberg'


class ApiTest(ResourceTestCase):

    def setUp(self):
        super(ApiTest, self).setUp()
        # Set up a user
        self.username = 'TestUser'
        self.password = 'password'
        self.user = User.objects.create(username=self.username, password=self.password)
        self.api_key = ApiKey.objects.create(user=self.user, key='testkey')

        self.port_node_type = NodeType.objects.create(type='Port', slug="port")
        self.cable_node_type = NodeType.objects.create(type='Cable', slug="cable")
        self.rack_node_type = NodeType.objects.create(type='Rack', slug="rack")

        self.DEFAULT_HANDLE_IDS = []

    def tearDown(self):
        for nh in NodeHandle.objects.all():
            nh.delete()
        with nc.graphdb.manager.session as s:
            s.run("MATCH (a:Node) OPTIONAL MATCH (a)-[r]-(b) DELETE a, b, r")
        super(ApiTest, self).tearDown()

    def get_credentials(self):
        return self.create_apikey(username=self.username, api_key=str(self.api_key.key))

    def test_list_nothing(self):
        resp = self.api_client.get('/api/v1/rack/', format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        self.assertGreaterEqual(len(self.deserialize(resp)['objects']), 0)

    def test_create_rack(self):
        node_name = 'Rack1'
        node_type = '/api/v1/node_type/rack/'
        node_meta_type = 'Location'
        data = {
            "node_name": "{}".format(node_name),
            "node_type": "{}".format(node_type),
            "node_meta_type": '{}'.format(node_meta_type),
        }
        resp = self.api_client.post('/api/v1/rack/', data=data, format='json', authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 201)
        resp = self.api_client.get(resp.get('Location'), format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        self.assertEqual(self.deserialize(resp).get('node_name'), node_name)

    def test_create_relationship(self):
        cable = NodeHandle.objects.create(
            node_name='12345678',
            node_type=self.cable_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )
        port = NodeHandle.objects.create(
            node_name='20',
            node_type=self.port_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )
        data = {
            "start": "/api/v1/cable/{}/".format(cable.node_name),
            "end": "/api/v1/port/{}/".format(port.handle_id),
            "type": "Connected_to"
        }
        resp = self.api_client.post('/api/v1/relationship/', format='json', data=data,
                                    authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        cable_node = cable.get_node()
        self.assertIsNotNone(cable_node.data.get('name', None))
        connections = cable_node.get_connected_equipment()
        self.assertEqual(len(connections), 1)
