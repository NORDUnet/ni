import datetime
from django.contrib.auth.models import User
from tastypie.test import ResourceTestCase
from tastypie.models import ApiKey
from apps.noclook.models import NodeHandle, NodeType, UniqueIdGenerator
from apps.noclook import helpers as h
import norduni_client as nc

class ServiceL2VPNResourceTest(ResourceTestCase):

    def setUp(self):
        super(ServiceL2VPNResourceTest, self).setUp()
        # Set up a user
        self.username = 'TestUser'
        self.password = 'password'
        self.user,created = User.objects.get_or_create(username=self.username,
                                                       password=self.password)
        self.api_key = ApiKey.objects.create(user=self.user, key='testkey')
        # Set up id generators
        #vpn_id_generator = UniqueIdGenerator.objects.get_or_create(
        #    name='nordunet_vpn_id'
        #)

        # Set up initial data
        router_node_type = NodeType.objects.create(type='Router', slug="router")
        port_node_type = NodeType.objects.create(type='Port', slug="port")
        router1, r1created = NodeHandle.objects.get_or_create(
            node_name = 'Test Router 1',
            node_type = router_node_type,
            node_meta_type = 'physical',
            creator = self.user,
            modifier = self.user,
        )
        router2, r2created = NodeHandle.objects.get_or_create(
            node_name = 'Test Router 2',
            node_type = router_node_type,
            node_meta_type = 'physical',
            creator = self.user,
            modifier = self.user,
        )
        port1, p1created = NodeHandle.objects.get_or_create(
            node_name = 'Test Port 1',
            node_type = port_node_type,
            node_meta_type = 'physical',
            creator = self.user,
            modifier = self.user,
        )
        port2, p2created = NodeHandle.objects.get_or_create(
            node_name = 'Test Port 2',
            node_type = port_node_type,
            node_meta_type = 'physical',
            creator = self.user,
            modifier = self.user,
        )
        if r1created and p1created:
            h.place_child_in_parent(port1.get_node(), router1.get_node().getId())
        if r2created and r2created:
            h.place_child_in_parent(port2.get_node(), router2.get_node().getId())

    def get_credentials(self):
        return self.create_apikey(username=self.username, api_key=str(self.api_key.key))

    def test_router_list(self):
        resp = self.api_client.get('/api/v1/router/', format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        self.assertGreaterEqual(len(self.deserialize(resp)['objects']), 2)

    def test_port_list(self):
        resp = self.api_client.get('/api/v1/router/', format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        self.assertGreaterEqual(len(self.deserialize(resp)['objects']), 2)


























