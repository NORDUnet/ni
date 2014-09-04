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
import sys


class ServiceL2VPNResourceTest(ResourceTestCase):

    # TODO: Write tests for this.
    # vpn creation:
    # url: https://nidev-consumer.nordu.net/api/v1/l2vpn/
    # {"ncs_service_name": "vpn-vlan-rewrite", "route_distinguisher": "2603:0093", "end_points": [{"device": "sto", "port": "ge-1\/0\/1", "unit": "1705", "vlan": "1705"}, {"device": "hel", "port": "ge-1\/0\/1", "unit": "1710", "vlan": "1710"}], "operational_state": "In service", "vpn_type": "l2vpn", "description": "NCS VPN:VPN created through NCS", "vlan": "1705 <->1710", "node_name": "NU-S800092", "vrf_target": "target:2603:4242000093"}
    # vpn update:
    # url: https://nidev-consumer.nordu.net/api/v1/l2vpn/NU-S800005
    # {"route_distinguisher": "2603:0007", "operational_state": "In service", "vpn_type": "l2vpn", "description": "VPN created by NCS", "vlan": 1704, "vrf_target": "target:2603:4242000007"}
    # vpn decommission:
    # TBA

    def setUp(self):
        super(ServiceL2VPNResourceTest, self).setUp()
        # Set up a user
        self.username = 'TestUser'
        self.password = 'password'
        self.user = User.objects.create(username=self.username, password=self.password)
        self.api_key = ApiKey.objects.create(user=self.user, key='testkey')

        # Set up an ID generator
        self.id_generator = UniqueIdGenerator.objects.create(
            name='nordunet_service_id',
            base_id_length=6,
            zfill=True,
            prefix='NU-S',
            creator=self.user
        )

        # Set up initial data
        router_node_type = NodeType.objects.create(type='Router', slug="router")
        port_node_type = NodeType.objects.create(type='Port', slug="port")
        unit_node_type = NodeType.objects.create(type='Unit', slug="unit")
        # Have to create a service type as services can't be created without it.
        service_node_type = NodeType.objects.create(type='Service', slug="service")
        self.router1 = NodeHandle.objects.create(
            node_name='Test Router 1',
            node_type=router_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )
        self.router2 = NodeHandle.objects.create(
            node_name='Test Router 2',
            node_type=router_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )
        self.port1 = NodeHandle.objects.create(
            node_name='Test Port 1',
            node_type=port_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )
        self.port2 = NodeHandle.objects.create(
            node_name='Test Port 2',
            node_type=port_node_type,
            node_meta_type='Physical',
            creator=self.user,
            modifier=self.user,
        )
        self.unit1 = NodeHandle.objects.create(
            node_name='Test Unit 1',
            node_type=unit_node_type,
            node_meta_type='Logical',
            creator=self.user,
            modifier=self.user,
        )
        self.unit2 = NodeHandle.objects.create(
            node_name='Test Unit 2',
            node_type=unit_node_type,
            node_meta_type='Logical',
            creator=self.user,
            modifier=self.user,
        )

        self.DEFAULT_HANDLE_IDS = [
            self.router1.handle_id,
            self.router2.handle_id,
            self.port1.handle_id,
            self.port2.handle_id,
            self.unit1.handle_id,
            self.unit2.handle_id
        ]

        helpers.set_has(self.user, self.router1.get_node(), self.port1.handle_id)
        helpers.set_has(self.user, self.router2.get_node(), self.port2.handle_id)
        helpers.set_part_of(self.user, self.port1.get_node(), self.unit1.handle_id)
        helpers.set_part_of(self.user, self.port2.get_node(), self.unit2.handle_id)

    def tearDown(self):
        for handle_id in self.DEFAULT_HANDLE_IDS:
            nh = NodeHandle.objects.get(pk=handle_id)
            nh.delete()
        super(ServiceL2VPNResourceTest, self).tearDown()

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

    def test_unit_list(self):
        resp = self.api_client.get('/api/v1/unit/', format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        self.assertGreaterEqual(len(self.deserialize(resp)['objects']), 1)

    #@override_settings(DEBUG=True)
    def test_create_l2vpn_existing_port_end_point(self):
        data = {
            "route_distinguisher": "2603:0007",
            "end_points": [
                {
                    "device": "Test Router 1",
                    "port": "Test Port 1"
                },
                {
                    "device": "Test Router 2",
                    "port": "Test Port 2"
                }
            ],
            "operational_state": "In service",
            "vpn_type": "l2vpn",
            "description": "VPN created by NOCLook test",
            "node_name": "ServiceID",
            "vrf_target": "target:2603:4242000007"
        }
        resp = self.api_client.post('/api/v1/l2vpn/', format='json', data=data, authentication=self.get_credentials())
        #sys.stderr.writelines('stderr: ' + str(resp))
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        self.DEFAULT_HANDLE_IDS.append(nh.handle_id)
        default_unit_1 = self.port1.get_node().get_unit('0').get('Part_of')[0]['node']
        default_unit_2 = self.port2.get_node().get_unit('0').get('Part_of')[0]['node']
        self.assertEqual(len(default_unit_1.relationships['Depends_on']), 1)
        self.assertEqual(len(default_unit_2.relationships['Depends_on']), 1)

    def test_create_l2vpn_new_port_end_point(self):
        data = {
            "route_distinguisher": "2603:0007",
            "end_points": [
                {
                    "device": "Test Router 1",
                    "port": "New Port 1"
                },
                {
                    "device": "Test Router 2",
                    "port": "New Port 2"
                }
            ],
            "operational_state": "In service",
            "vpn_type": "l2vpn",
            "description": "VPN created by NOCLook test",
            "node_name": "ServiceID",
            "vrf_target": "target:2603:4242000007"
        }
        resp = self.api_client.post('/api/v1/l2vpn/', format='json', data=data, authentication=self.get_credentials())
        #sys.stderr.writelines('stderr: ' + str(resp))
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        self.DEFAULT_HANDLE_IDS.append(nh.handle_id)
        new_port_1 = self.router1.get_node().get_port('New Port 1').get('Has')[0]['node']
        new_port_2 = self.router2.get_node().get_port('New Port 2').get('Has')[0]['node']
        default_unit_1 = new_port_1.get_unit('0').get('Part_of')[0]['node']
        default_unit_2 = new_port_2.get_unit('0').get('Part_of')[0]['node']
        self.assertEqual(len(default_unit_1.relationships['Depends_on']), 1)
        self.assertEqual(len(default_unit_2.relationships['Depends_on']), 1)

    #@override_settings(DEBUG=True)
    def test_create_l2vpn_existing_unit_end_point(self):
        data = {
            "route_distinguisher": "2603:0007",
            "end_points": [
                {
                    "device": "Test Router 1",
                    "port": "Test Port 1",
                    "unit": "Test Unit 1"
                },
                {
                    "device": "Test Router 2",
                    "port": "Test Port 2"
                }
            ],
            "operational_state": "In service",
            "vpn_type": "l2vpn",
            "description": "VPN created by NOCLook test",
            "vlan": 1704,
            "node_name": "ServiceID",
            "vrf_target": "target:2603:4242000007"
        }
        resp = self.api_client.post('/api/v1/l2vpn/', format='json', data=data, authentication=self.get_credentials())
        #sys.stderr.writelines('stderr: ' + str(resp))
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        self.DEFAULT_HANDLE_IDS.append(nh.handle_id)
        self.assertEqual(len(self.unit1.get_node().relationships['Depends_on']), 1)

    def test_create_l2vpn_new_unit_end_point(self):
        data = {
            "route_distinguisher": "2603:0007",
            "end_points": [
                {
                    "device": "Test Router 1",
                    "port": "Test Port 1",
                    "unit": "New Unit 1"
                },
                {
                    "device": "Test Router 2",
                    "port": "Test Port 2",
                    "unit": "New Unit 2"
                }
            ],
            "operational_state": "In service",
            "vpn_type": "l2vpn",
            "description": "VPN created by NOCLook test",
            "vlan": 1704,
            "node_name": "ServiceID",
            "vrf_target": "target:2603:4242000007"
        }
        resp = self.api_client.post('/api/v1/l2vpn/', format='json', data=data, authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        self.DEFAULT_HANDLE_IDS.append(nh.handle_id)
        new_unit_1 = self.port1.get_node().get_unit('New Unit 1').get('Part_of')[0]['node']
        new_unit_2 = self.port2.get_node().get_unit('New Unit 2').get('Part_of')[0]['node']
        self.assertEqual(len(new_unit_1.relationships['Depends_on']), 1)
        self.assertEqual(len(new_unit_2.relationships['Depends_on']), 1)

    def test_update_l2vpn(self):
        data = {
            "route_distinguisher": "2603:0007",
            "end_points": [
                {
                    "device": "Test Router 1",
                    "port": "Test Port 1",
                    "unit": "Test Unit 1"
                },
                {
                    "device": "Test Router 2",
                    "port": "Test Port 2",
                    "unit": "Test Unit 2"
                }
            ],
            "operational_state": "In service",
            "vpn_type": "l2vpn",
            "description": "VPN created by NOCLook test",
            "vlan": 1704,
            "node_name": "ServiceID",
            "vrf_target": "target:2603:4242000007"
        }
        resp = self.api_client.post('/api/v1/l2vpn/', format='json', data=data, authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        self.DEFAULT_HANDLE_IDS.append(nh.handle_id)
        data = {
            "route_distinguisher": "new-2603:0007",
            "operational_state": "Decommissioned",
            "vpn_type": "l2vpn",
            "description": "VPN updated by NOCLook test",
            "vlan": 4071,
            "vrf_target": "new-target:2603:4242000007"
        }
        resp = self.api_client.put('/api/v1/l2vpn/ServiceID/', format='json', data=data,
                                   authentication=self.get_credentials())
        self.assertHttpOK(resp)

    def test_failed_update_l2vpn(self):
        data = {
            "route_distinguisher": "2603:0007",
            "end_points": [
                {
                    "device": "Test Router 1",
                    "port": "Test Port 1",
                    "unit": "Test Unit 1"
                },
                {
                    "device": "Test Router 2",
                    "port": "Test Port 2",
                    "unit": "Test Unit 2"
                }
            ],
            "operational_state": "In service",
            "vpn_type": "l2vpn",
            "description": "VPN created by NOCLook test",
            "vlan": 1704,
            "node_name": "ServiceID",
            "vrf_target": "target:2603:4242000007"
        }
        resp = self.api_client.post('/api/v1/l2vpn/', format='json', data=data, authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        self.DEFAULT_HANDLE_IDS.append(nh.handle_id)
        data = {
            "operational_state": "Not in service",
        }
        resp = self.api_client.put('/api/v1/l2vpn/ServiceID/', format='json', data=data, authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 406)  # NotAcceptable

    def test_update_l2vpn_new_end_point(self):
        data = {
            "route_distinguisher": "2603:0007",
            "end_points": [
                {
                    "device": "Test Router 1",
                    "port": "Test Port 1",
                    "unit": "Test Unit 1"
                },
                {
                    "device": "Test Router 2",
                    "port": "Test Port 2",
                    "unit": "Test Unit 2"
                }
            ],
            "operational_state": "In service",
            "vpn_type": "l2vpn",
            "description": "VPN created by NOCLook test",
            "vlan": 1704,
            "node_name": "ServiceID",
            "vrf_target": "target:2603:4242000007"
        }
        resp = self.api_client.post('/api/v1/l2vpn/', format='json', data=data, authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        self.DEFAULT_HANDLE_IDS.append(nh.handle_id)
        self.assertEqual(len(self.unit1.get_node().relationships['Depends_on']), 1)
        self.assertEqual(len(self.unit2.get_node().relationships['Depends_on']), 1)

        data = {
            "end_points": [
                {
                    "device": "Test Router 1",
                    "port": "Test Port 1",
                    "unit": "New Unit 1"
                },
                {
                    "device": "Test Router 2",
                    "port": "Test Port 2",
                    "unit": "New Unit 2"
                }
            ],
        }
        resp = self.api_client.put('/api/v1/l2vpn/ServiceID/', format='json', data=data,
                                   authentication=self.get_credentials())
        self.assertHttpOK(resp)
        new_unit_1 = self.port1.get_node().get_unit('New Unit 1').get('Part_of')[0]['node']
        new_unit_2 = self.port2.get_node().get_unit('New Unit 2').get('Part_of')[0]['node']
        self.assertEqual(len(new_unit_1.relationships['Depends_on']), 1)
        self.assertEqual(len(new_unit_2.relationships['Depends_on']), 1)

    def test_create_interface_switch_new_unit_end_point(self):
        data = {
            "end_points": [
                {
                    "device": "Test Router 1",
                    "port": "Test Port 1",
                    "unit": "New Unit 1"
                },
                {
                    "device": "Test Router 2",
                    "port": "Test Port 2",
                    "unit": "New Unit 2"
                }
            ],
            "operational_state": "In service",
            "vpn_type": "interface-switch",
            "description": "Interface Switch created by NOCLook test",
            "vlan": 1704,
            "node_name": "ServiceID"
        }
        resp = self.api_client.post('/api/v1/l2vpn/', format='json', data=data, authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        self.DEFAULT_HANDLE_IDS.append(nh.handle_id)
        new_unit_1 = self.port1.get_node().get_unit('New Unit 1')['Part_of'][0]['node']
        new_unit_2 = self.port2.get_node().get_unit('New Unit 2')['Part_of'][0]['node']
        self.assertEqual(len(new_unit_1.relationships['Depends_on']), 1)
        self.assertEqual(len(new_unit_2.relationships['Depends_on']), 1)

    def test_create_interface_switch_trunk_existing_port_end_point(self):
        data = {
            "end_points": [
                {
                    "device": "Test Router 1",
                    "port": "Test Port 1"
                },
                {
                    "device": "Test Router 2",
                    "port": "Test Port 2"
                }
            ],
            "operational_state": "In service",
            "vpn_type": "interface-switch",
            "description": "VPN created by NOCLook test",
            "node_name": "ServiceID",
        }
        resp = self.api_client.post('/api/v1/l2vpn/', format='json', data=data, authentication=self.get_credentials())
        #sys.stderr.writelines('stderr: ' + str(resp))
        self.assertHttpCreated(resp)
        nh = NodeHandle.objects.get(handle_id=self.deserialize(resp)['handle_id'])
        self.DEFAULT_HANDLE_IDS.append(nh.handle_id)
        default_unit_1 = self.port1.get_node().get_unit('0').get('Part_of')[0]['node']
        default_unit_2 = self.port2.get_node().get_unit('0').get('Part_of')[0]['node']
        self.assertEqual(len(default_unit_1.relationships['Depends_on']), 1)
        self.assertEqual(len(default_unit_2.relationships['Depends_on']), 1)