# -*- coding: utf-8 -*-
"""
Created on 2014-06-26 1:28 PM

@author: lundberg
"""

from django.contrib.auth.models import User
from tastypie.test import ResourceTestCase
from tastypie.models import ApiKey
from apps.noclook.models import NodeHandle, NodeType, UniqueIdGenerator, UniqueId
from apps.noclook import helpers as h
import norduni_client as nc

import sys


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
        router_node_type = NodeType.objects.create(type='Router', slug="router")
        port_node_type = NodeType.objects.create(type='Port', slug="port")
        cable_node_type = NodeType.objects.create(type='Cable', slug="cable")
        # Have to create a service type as services can't be created without it.
        service_node_type = NodeType.objects.create(type='Service', slug="service")
        self.router1 = NodeHandle.objects.create(
            node_name='Test Router 1',
            node_type=router_node_type,
            node_meta_type='physical',
            creator=self.user,
            modifier=self.user,
        )
        self.router2 = NodeHandle.objects.create(
            node_name='Test Router 2',
            node_type=router_node_type,
            node_meta_type='physical',
            creator=self.user,
            modifier=self.user,
        )
        self.port1 = NodeHandle.objects.create(
            node_name='Test Port 1',
            node_type=port_node_type,
            node_meta_type='physical',
            creator=self.user,
            modifier=self.user,
        )
        self.port2 = NodeHandle.objects.create(
            node_name='Test Port 2',
            node_type=port_node_type,
            node_meta_type='physical',
            creator=self.user,
            modifier=self.user,
        )
        h.place_child_in_parent(self.user, self.port1.get_node(), self.router1.get_node().getId())
        h.place_child_in_parent(self.user, self.port2.get_node(), self.router2.get_node().getId())

    def purge_neo4jdb(self):
        for node in nc.get_all_nodes(nc.neo4jdb):
            if node.getId() != 0:
                nc.delete_node(nc.neo4jdb, node)

    def get_credentials(self):
        return self.create_apikey(username=self.username, api_key=str(self.api_key.key))

    def test_router_list(self):
        resp = self.api_client.get('/api/v1/router/', format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        self.assertGreaterEqual(len(self.deserialize(resp)['objects']), 2)
        self.purge_neo4jdb()

    def test_port_list(self):
        resp = self.api_client.get('/api/v1/port/', format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        self.assertGreaterEqual(len(self.deserialize(resp)['objects']), 2)
        self.purge_neo4jdb()

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
        self.assertEqual(cable_node['name'], data['node_name'])
        connections = h.get_connected_cables(cable_node)
        self.assertEqual(len(connections), 2)
        self.purge_neo4jdb()

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
        self.assertEqual(cable_node['name'], data['node_name'])
        connections = h.get_connected_cables(cable_node)
        self.assertEqual(len(connections), 2)
        self.purge_neo4jdb()

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
        self.assertIsNotNone(cable_node.get_property('name', None))
        connections = h.get_connected_cables(cable_node)
        self.assertEqual(len(connections), 2)
        self.purge_neo4jdb()

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
        self.assertIsNotNone(cable_node.get_property('name', None))
        connections = h.get_connected_cables(cable_node)
        self.assertEqual(len(connections), 2)
        self.purge_neo4jdb()

    def test_create_cable_name_conflict(self):
        data = {
            "node_name": "External Cable",
            "cable_type": "Patch",
        }
        resp = self.api_client.post('/api/v1/cable/', format='json', data=data, authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        resp = self.api_client.post('/api/v1/cable/', format='json', data=data, authentication=self.get_credentials())
        self.assertHttpConflict(resp)
        self.purge_neo4jdb()

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
        self.purge_neo4jdb()