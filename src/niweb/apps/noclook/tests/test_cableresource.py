# -*- coding: utf-8 -*-
"""
Created on 2014-06-26 1:28 PM

@author: lundberg
"""

from django.contrib.auth.models import User
from tastypie.test import ResourceTestCase
from tastypie.models import ApiKey
from apps.noclook.models import NodeHandle, NodeType, UniqueIdGenerator
from apps.noclook import helpers
import norduniclient as nc

# Use test instance of the neo4j db
nc.neo4jdb = nc.init_db('http://localhost:7475')

class CableResourceTest(ResourceTestCase):

    def setUp(self):
        super(CableResourceTest, self).setUp()
        # Set up a user
        self.username = 'TestUser'
        self.password = 'password'
        self.user = User.objects.create(username=self.username, password=self.password)
        self.api_key = ApiKey.objects.create(user=self.user, key='testkey')

        # Set up an ID generator
        self.id_generator = UniqueIdGenerator.objects.create(
            name='nordunet_cable_id',
            base_id_length=6,
            zfill=True,
            prefix='NU-0',
            creator=self.user
        )

        # Set up initial data
        self.router_node_type = NodeType.objects.create(type='Router', slug="router")
        self.port_node_type = NodeType.objects.create(type='Port', slug="port")
        self.cable_node_type = NodeType.objects.create(type='Cable', slug="cable")
        self.optical_node_node_type = NodeType.objects.create(type='Optical Node', slug="optical-node")
        # Have to create a service type as services can't be created without it.
        self.service_node_type = NodeType.objects.create(type='Service', slug="service")
        self.router1 = NodeHandle.objects.create(
            node_name='Test Router 1',
            node_type=self.router_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )
        self.router2 = NodeHandle.objects.create(
            node_name='Test Router 2',
            node_type=self.router_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )
        self.port1 = NodeHandle.objects.create(
            node_name='Test Port 1',
            node_type=self.port_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )
        self.port2 = NodeHandle.objects.create(
            node_name='Test Port 2',
            node_type=self.port_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )

        helpers.set_has(self.user, self.router1.get_node(), self.port1.handle_id)
        helpers.set_has(self.user, self.router2.get_node(), self.port2.handle_id)

    def tearDown(self):
        for nh in NodeHandle.objects.all():
            nh.delete()
        with nc.neo4jdb.transaction as t:
            t.execute("MATCH (a:Node) OPTIONAL MATCH (a)-[r]-(b) DELETE a, b, r").fetchall()
        super(CableResourceTest, self).tearDown()

    def get_credentials(self):
        return self.create_apikey(username=self.username, api_key=str(self.api_key.key))

    def test_router_list(self):
        resp = self.api_client.get('/api/v1/router/', format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        self.assertGreaterEqual(len(self.deserialize(resp)['objects']), 2)

    def test_port_list(self):
        resp = self.api_client.get('/api/v1/port/', format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        self.assertGreaterEqual(len(self.deserialize(resp)['objects']), 2)

    #@override_settings(DEBUG=True)
    def test_create_cable_existing_end_points(self):
        data = {
            "end_points": [
                {
                    "device": "Test Router 1",
                    "device_type": "Router",
                    "port": "Test Port 1"
                },
                {
                    "device": "Test Router 2",
                    "device_type": "Router",
                    "port": "Test Port 2"
                }
            ],
            "cable_type": "Patch",
            "node_name": "External Cable",
        }
        resp = self.api_client.post('/api/v1/cable/', format='json', data=data, authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        cable_node = nh.get_node()
        self.assertEqual(nh.node_name, data['node_name'])
        #sys.stderr.writelines('stderr: ' + str(cable_node))
        self.assertEqual(cable_node.data['name'], data['node_name'])
        connections = cable_node.get_connected_equipment()
        self.assertEqual(len(connections), 2)

    def test_create_cable_new_end_points(self):
        data = {
            "end_points": [
                {
                    "device": "Test Router 1",
                    "device_type": "Router",
                    "port": "Test Port 3"
                },
                {
                    "device": "Test Router 2",
                    "device_type": "Router",
                    "port": "Test Port 4"
                }
            ],
            "cable_type": "Patch",
            "node_name": "External Cable",
        }
        resp = self.api_client.post('/api/v1/cable/', format='json', data=data, authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        cable_node = nh.get_node()
        self.assertEqual(cable_node.data['name'], data['node_name'])
        connections = cable_node.get_connected_equipment()
        self.assertEqual(len(connections), 2)

    def test_create_nordunet_cable_existing_end_points(self):
        data = {
            "end_points": [
                {
                    "device": "Test Router 1",
                    "device_type": "Router",
                    "port": "Test Port 1"
                },
                {
                    "device": "Test Router 2",
                    "device_type": "Router",
                    "port": "Test Port 2"
                }
            ],
            "cable_type": "Patch",
        }
        resp = self.api_client.post('/api/v1/nordunet-cable/', format='json', data=data,
                                    authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        cable_node = nh.get_node()
        self.assertIsNotNone(cable_node.data.get('name', None))
        connections = cable_node.get_connected_equipment()
        self.assertEqual(len(connections), 2)

    def test_create_nordunet_cable_new_end_points(self):
        data = {
            "end_points": [
                {
                    "device": "Test Router 1",
                    "device_type": "Router",
                    "port": "Test Port 3"
                },
                {
                    "device": "Test Router 2",
                    "device_type": "Router",
                    "port": "Test Port 4"
                }
            ],
            "cable_type": "Patch",
        }
        resp = self.api_client.post('/api/v1/nordunet-cable/', format='json', data=data,
                                    authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        cable_node = nh.get_node()
        self.assertIsNotNone(cable_node.data.get('name', None))
        connections = cable_node.get_connected_equipment()
        self.assertEqual(len(connections), 2)

    def test_create_cable_name_conflict(self):
        data = {
            "node_name": "External Cable",
            "cable_type": "Patch",
        }
        resp = self.api_client.post('/api/v1/cable/', format='json', data=data, authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        resp = self.api_client.post('/api/v1/cable/', format='json', data=data, authentication=self.get_credentials())
        self.assertHttpConflict(resp)

    def test_create_nordunet_cable_name_conflict(self):
        data = {
            "node_name": "NU-00000001",
            "cable_type": "Patch",
        }
        resp = self.api_client.post('/api/v1/nordunet-cable/', format='json', data=data,
                                    authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        resp = self.api_client.post('/api/v1/nordunet-cable/', format='json', data=data,
                                    authentication=self.get_credentials())
        self.assertHttpConflict(resp)

    def test_optical_node_cable_bug(self):
        optical_node = NodeHandle.objects.create(
            node_name='NIK-ILA1-1',
            node_type=self.optical_node_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )
        data = {
            "node_name": "NIK-02",
            "cable_type": "Patch",
            "end_points": [
                {"device": "NIK-ILA1-1", "device_type": "Optical Node", "port": "01-NW"}
            ]
        }
        resp = self.api_client.put('/api/v1/cable/NIK-02/', format='json', data=data,
                                   authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        cable_node = nh.get_node()
        connections = cable_node.get_connected_equipment()
        self.assertEqual(len(connections), 1)

    def test_optical_node_cable_bug2(self):
        optical_node = NodeHandle.objects.create(
            node_name='NIK-ILA1-1',
            node_type=self.optical_node_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )
        data = {
            "node_name": "NIK-02",
            "cable_type": "Patch",
            "end_points": [
                {"device": "NIK-ILA1-1", "device_type": "Optical Node", "port": "01-NW"}
            ]
        }
        resp = self.api_client.put('/api/v1/cable/NIK-02/', format='json', data=data,
                                   authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        cable_node = nh.get_node()
        connections = cable_node.get_connected_equipment()

        self.assertEqual(len(connections), 1)
        data = {
            "node_name": "NIK-02",
            "cable_type": "Patch",
            "end_points": [
                {"device": "NIK-ILA1-1", "device_type": "Optical Node", "port": "01-NW"},
                {"device": "NIK-ILA1-1", "device_type": "Optical Node", "port": "02-NW"}
            ]
        }
        resp = self.api_client.put('/api/v1/cable/NIK-02/', format='json', data=data,
                                   authentication=self.get_credentials())
        self.assertHttpOK(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        cable_node = nh.get_node()
        connections = cable_node.get_connected_equipment()
        self.assertEqual(len(connections), 2)

