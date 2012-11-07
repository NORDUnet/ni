import datetime
from django.test import TestCase
from django.db import connection, DatabaseError
from django.contrib.auth.models import User
from tastypie.test import ResourceTestCase
from tastypie.models import ApiKey
from apps.noclook.models import NodeHandle, NodeType, UniqueIdGenerator, UniqueId
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


class UniqueIdGeneration(TestCase):

    def setUp(self):
        # Set up a user
        self.username = 'TestUser'
        self.password = 'password'
        self.user,created = User.objects.get_or_create(username=self.username,
            password=self.password)
        # Set up an ID generator
        self.id_generator, created = UniqueIdGenerator.objects.get_or_create(
            name='Test ID Generator',
            base_id_length=6,
            zfill=True,
            prefix='TEST-',
            creator=self.user
        )
        # Set up an ID collection
        try:
            connection.cursor().execute("""
                CREATE TABLE "noclook_testuniqueid" (
                    "id" integer NOT NULL PRIMARY KEY,
                    "unique_id" varchar(256) NOT NULL UNIQUE,
                    "reserved" bool NOT NULL,
                    "reserve_message" varchar(512),
                    "reserver_id" integer REFERENCES "auth_user" ("id"),                                                                                                                             "created" datetime NOT NULL
                );
                """)
        except DatabaseError:
            # Table already created
            pass
        class TestUniqueId(UniqueId):
            def __unicode__(self):
                return unicode('Test: %s' % self.unique_id)
        self.id_collection = TestUniqueId

    def test_id_generation(self):
        new_id = self.id_generator.get_id()
        self.assertEqual(new_id, self.id_generator.last_id)
        unique_id = self.id_collection.objects.create(unique_id=new_id)
        self.assertEqual(unique_id.unique_id, new_id)

    def test_helper_functions_basics(self):
        new_id = self.id_generator.get_id()
        return_value = h.register_unique_id(self.id_collection, new_id)
        self.assertEqual(return_value, True)
        next_id = self.id_generator.next_id
        new_id = h.get_collection_unique_id(self.id_generator, self.id_collection)
        self.assertEqual(new_id, next_id)

    def test_bulk_reserve(self):
        h.bulk_reserve_ids(1, 100, self.id_generator, self.id_collection, 'Reserve message', self.user)
        num_objects = self.id_collection.objects.count()
        self.assertEqual(num_objects, 100)

    def test_get_unique_id_jump(self):
        h.bulk_reserve_ids(1, 99, self.id_generator, self.id_collection, 'Reserve message', self.user)
        self.assertEqual(self.id_generator.next_id, 'TEST-000001')
        new_id = h.get_collection_unique_id(self.id_generator, self.id_collection)
        self.assertEqual(new_id, 'TEST-000100')
        h.bulk_reserve_ids(101, 199, self.id_generator, self.id_collection, 'Reserve message', self.user)
        new_id = h.get_collection_unique_id(self.id_generator, self.id_collection)
        self.assertEqual(new_id, 'TEST-000200')























