import datetime
from django.test import TestCase
from django.test.utils import override_settings
from django.db import connection, transaction, IntegrityError
from django.contrib.auth.models import User
from tastypie.test import ResourceTestCase
from tastypie.models import ApiKey
from apps.noclook.models import NodeHandle, NodeType, UniqueIdGenerator, UniqueId
from apps.noclook import helpers as h
import norduni_client as nc
import sys


class ServiceL2VPNResourceTest(ResourceTestCase):

    # TODO: Write tests for this.
    # vpn creation:
    # url: https://nidev-consumer.nordu.net/api/v1/l2vpn/
    # {"route_distinguisher":"2603:0007","end_points":[{"device":"hel","port":"ge-1\/0\/1"},{"device":"sto","port":"ge-1\/0\/1"}],"operational_state":"In service","interface_type":"ethernet-vlan","vpn_type":"l2vpn","description":"VPN created by NCS","vlan":1704,"node_name":"NU-S800005","vrf_target":"target:2603:4242000007"}
    # vpn update:
    # url: https://nidev-consumer.nordu.net/api/v1/l2vpn/NU-S800005
    # {"route_distinguisher": "2603:0007", "operational_state": "In service", "interface_type": "ethernet-vlan", "vpn_type": "l2vpn", "description": "VPN created by NCS", "vlan": 1704, "vrf_target": "target:2603:4242000007"}
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
        self.unit1 = NodeHandle.objects.create(
            node_name='Test Unit 1',
            node_type=unit_node_type,
            node_meta_type='logical',
            creator=self.user,
            modifier=self.user,
        )
        self.unit2 = NodeHandle.objects.create(
            node_name='Test Unit 2',
            node_type=unit_node_type,
            node_meta_type='logical',
            creator=self.user,
            modifier=self.user,
        )
        h.place_child_in_parent(self.user, self.port1.get_node(), self.router1.get_node().getId())
        h.place_child_in_parent(self.user, self.port2.get_node(), self.router2.get_node().getId())
        nc.create_relationship(nc.neo4jdb, self.unit1.get_node(), self.port1.get_node(), 'Part_of')
        nc.create_relationship(nc.neo4jdb, self.unit2.get_node(), self.port2.get_node(), 'Part_of')

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

    def test_unit_list(self):
        resp = self.api_client.get('/api/v1/unit/', format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        self.assertGreaterEqual(len(self.deserialize(resp)['objects']), 1)
        self.purge_neo4jdb()

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
            "interface_type": "ethernet-vlan",
            "vpn_type": "l2vpn",
            "description": "VPN created by NOCLook test",
            "vlan": 1704,
            "node_name": "Service ID 1",
            "vrf_target": "target:2603:4242000007"
        }
        resp = self.api_client.post('/api/v1/l2vpn/', format='json', data=data, authentication=self.get_credentials())
        #sys.stderr.writelines('stderr: ' + str(resp))
        self.assertHttpCreated(resp)
        self.assertEqual(len([hit for hit in self.port1.get_node().Depends_on]), 1)
        self.assertEqual(len([hit for hit in self.port2.get_node().Depends_on]), 1)
        self.purge_neo4jdb()

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
            "interface_type": "ethernet-vlan",
            "vpn_type": "l2vpn",
            "description": "VPN created by NOCLook test",
            "vlan": 1704,
            "node_name": "Service ID 2",
            "vrf_target": "target:2603:4242000007"
        }
        resp = self.api_client.post('/api/v1/l2vpn/', format='json', data=data, authentication=self.get_credentials())
        #sys.stderr.writelines('stderr: ' + str(resp))
        self.assertHttpCreated(resp)
        new_port_1 = h.get_port('Test Router 1', 'New Port 1')
        new_port_2 = h.get_port('Test Router 2', 'New Port 2')
        self.assertEqual(len([hit for hit in new_port_1.Depends_on]), 1)
        self.assertEqual(len([hit for hit in new_port_2.Depends_on]), 1)
        self.purge_neo4jdb()

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
            "interface_type": "ethernet-vlan",
            "vpn_type": "l2vpn",
            "description": "VPN created by NOCLook test",
            "vlan": 1704,
            "node_name": "Service ID 3",
            "vrf_target": "target:2603:4242000007"
        }
        resp = self.api_client.post('/api/v1/l2vpn/', format='json', data=data, authentication=self.get_credentials())
        #sys.stderr.writelines('stderr: ' + str([hit for hit in self.unit1.get_node().rels]))
        self.assertHttpCreated(resp)
        self.assertEqual(len([hit for hit in self.unit1.get_node().Depends_on]), 1)
        self.purge_neo4jdb()


class UniqueIdGeneration(TestCase):

    #@transaction.autocommit
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
        #try:
        # sqlite3
#        connection.cursor().execute("""
#            CREATE TABLE "noclook_testuniqueid" (
#                "id" integer NOT NULL PRIMARY KEY,
#                "unique_id" varchar(256) NOT NULL UNIQUE,
#                "reserved" bool NOT NULL,
#                "reserve_message" varchar(512),
#                "reserver_id" integer REFERENCES "auth_user" ("id"),
#                "created" datetime NOT NULL
#            );
#            """)
        # postgresql
        connection.cursor().execute("""
                CREATE TABLE "noclook_testuniqueid" (
                    "id" serial NOT NULL PRIMARY KEY,
                    "unique_id" varchar(256) NOT NULL UNIQUE,
                    "reserved" boolean NOT NULL,
                    "reserve_message" varchar(512),
                    "reserver_id" integer REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
                    "created" timestamp with time zone NOT NULL
                );
                """)
        #except DatabaseError as e:
            # Table already created
            #print e
            #pass
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

    def test_reserve_range(self):
        h.bulk_reserve_id_range(1, 100, self.id_generator, self.id_collection, 'Reserve message', self.user)
        num_objects = self.id_collection.objects.count()
        self.assertEqual(num_objects, 100)
        new_id = h.get_collection_unique_id(self.id_generator, self.id_collection)
        self.assertEqual(new_id, 'TEST-000101')

    def test_reserve_sequence(self):
        h.reserve_id_sequence(100, self.id_generator, self.id_collection, 'Reserve message', self.user)
        num_objects = self.id_collection.objects.count()
        self.assertEqual(num_objects, 100)
        new_id = h.get_collection_unique_id(self.id_generator, self.id_collection)
        self.assertEqual(new_id, 'TEST-000101')


    def test_get_unique_id_jump(self):
        h.bulk_reserve_id_range(1, 99, self.id_generator, self.id_collection, 'Reserve message', self.user)
        self.assertEqual(self.id_generator.next_id, 'TEST-000001')
        new_id = h.get_collection_unique_id(self.id_generator, self.id_collection)
        self.assertEqual(new_id, 'TEST-000100')
        h.bulk_reserve_id_range(101, 150, self.id_generator, self.id_collection, 'Reserve message', self.user)
        seq = h.reserve_id_sequence(100, self.id_generator, self.id_collection, 'Reserve message', self.user)
        self.assertEqual(len(seq), 100)
        new_id = h.get_collection_unique_id(self.id_generator, self.id_collection)
        self.assertEqual(new_id, 'TEST-000201')

    def test_register_reserved_id(self):
        h.bulk_reserve_id_range(1, 99, self.id_generator, self.id_collection, 'Reserve message', self.user)
        result = h.register_unique_id(self.id_collection, 'TEST-000001')
        self.assertTrue(result)

    def test_register_unreserved_id(self):
        result = h.register_unique_id(self.id_collection, 'TEST-000001')
        self.assertTrue(result)

    def test_register_used_id(self):
        result = h.register_unique_id(self.id_collection, 'TEST-000001')
        self.assertTrue(result)
        try:
            sid = transaction.savepoint()
            h.register_unique_id(self.id_collection, 'TEST-000001')
            transaction.savepoint_commit(sid)
        except IntegrityError as e:
            transaction.savepoint_rollback(sid)
        self.assertIsInstance(e, IntegrityError)























