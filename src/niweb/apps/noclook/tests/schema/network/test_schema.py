# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.schema.query import NOCRootQuery, \
                                        network_org_types, host_owner_types, \
                                        optical_path_dependency_types
from apps.noclook.models import ServiceClass
from django.core.management import call_command
from graphene import relay
from niweb.schema import schema
from pprint import pformat

from . import Neo4jGraphQLNetworkTest

import random
import os

class NetworkOrganizationsTest(Neo4jGraphQLNetworkTest):
    def test_network_organizations(self):
        ## network types query
        query = '''
        {
          getNetworkOrgTypes{
            type_name
            connection_name
            byid_name
            all_name
          }
        }
        '''

        expected = {
            "getNetworkOrgTypes": [
                {
                    "type_name": "Customer",
                    "connection_name": "customers",
                    "byid_name": "getCustomerById",
                    "all_name": "all_customers"
                },
                {
                    "type_name": "EndUser",
                    "connection_name": "endUsers",
                    "byid_name": "getEndUserById",
                    "all_name": "all_endusers"
                },
                {
                    "type_name": "Provider",
                    "connection_name": "providers",
                    "byid_name": "getProviderById",
                    "all_name": "all_providers"
                },
                {
                    "type_name": "SiteOwner",
                    "connection_name": "siteOwners",
                    "byid_name": "getSiteOwnerById",
                    "all_name": "all_siteowners"
                }
            ]
        }

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors

        self.assertEqual(result.data, expected)


class HostOwnerTest(Neo4jGraphQLNetworkTest):
    def test_host_owner_types(self):
        ## host owner query
        query = '''
        {
          getHostOwnerTypes{
            type_name
            connection_name
            byid_name
            all_name
          }
        }
        '''

        expected = {
            "getHostOwnerTypes": [
                {
                    "type_name": "Customer",
                    "connection_name": "customers",
                    "byid_name": "getCustomerById",
                    "all_name": "all_customers"
                },
                {
                    "type_name": "EndUser",
                    "connection_name": "endUsers",
                    "byid_name": "getEndUserById",
                    "all_name": "all_endusers"
                },
                {
                    "type_name": "Provider",
                    "connection_name": "providers",
                    "byid_name": "getProviderById",
                    "all_name": "all_providers"
                },
                {
                    "type_name": "HostUser",
                    "connection_name": "hostUsers",
                    "byid_name": "getHostUserById",
                    "all_name": "all_hostusers"
                }
            ]
        }

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors

        self.assertEqual(result.data, expected)


class OpticalPathDependencyTypesTest(Neo4jGraphQLNetworkTest):
    def test_optical_path_dependency_types(self):
        query = '''
        {
          getOpticalPathDependencyTypes{
            type_name
            connection_name
            byid_name
            all_name
          }
        }
        '''

        expected = {
            "getOpticalPathDependencyTypes": []
        }

        for clazz in optical_path_dependency_types:
            byid_name = NOCRootQuery.\
                graph_by_id_type_resolvers[clazz]['field_name']

            connection_name = NOCRootQuery.\
                graph_connection_type_resolvers[clazz]['field_name']

            all_name = NOCRootQuery.\
                graph_all_type_resolvers[clazz]['field_name']

            dict_obj = {
                "type_name": "{}".format(clazz),
                "connection_name": connection_name,
                "byid_name": byid_name,
                "all_name": all_name
            }
            expected["getOpticalPathDependencyTypes"].append(dict_obj)

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors

        self.assertEqual(result.data, expected)



class ServiceClassConnectionTest(Neo4jGraphQLNetworkTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)

        # import service classes and types
        dirpath = os.path.dirname(os.path.realpath(__file__))
        csv_file = \
            '{}/../../../../../../scripts/service_types/ndn_service_types.csv'\
                .format(dirpath)

        call_command(
            'import_service_types',
            csv_file=csv_file
        )

    def test_service_class_connection(self):
        filter_t = '( filter: {{ {} }} )'
        order_t = '( orderBy: {} )'
        filter_order_t = '( filter: {{ {} }}, orderBy: {} )'

        query_t = """
        {{
          services_classes
          {filter_order}
          {{
            edges{{
              node{{
                id
                name
                servicetype_set{{
                  edges{{
                    node{{
                      id
                      name
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
        """

        # no filter nor order
        filter_order = ''
        query = query_t.format(filter_order=filter_order)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        edges = result.data['services_classes']['edges']
        res_sclasnames = [ x['node']['name'] for x in edges ]
        expected = [x.name for x in ServiceClass.objects.all()]

        self.assertEquals(res_sclasnames, expected)

        # id filter
        rand_serv_class = random.choice(ServiceClass.objects.all())
        sclass_id = relay.Node.to_global_id( 'ServiceClass',
            str(rand_serv_class.id))

        filter_order = filter_t.format( 'id: "{}"'.format(sclass_id) )
        query = query_t.format(filter_order=filter_order)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        edges = result.data['services_classes']['edges']
        res_sclasnames = [ x['node']['name'] for x in edges ]
        expected = [rand_serv_class.name]

        self.assertEquals(res_sclasnames, expected)

        # name filter
        # so we get Ethernet, External and Internal
        filter_order = filter_t.format( 'name_contains: "er"' )
        query = query_t.format(filter_order=filter_order)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        edges = result.data['services_classes']['edges']
        res_sclasnames = [ x['node']['name'] for x in edges ]
        expected = ['Ethernet', 'External', 'Internal']

        self.assertEquals(res_sclasnames, expected)

        # reverse alphabetical order
        filter_order = order_t.format('name_ASC')
        query = query_t.format(filter_order=filter_order)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        edges = result.data['services_classes']['edges']
        res_sclasnames = [ x['node']['name'] for x in edges ]
        expected = [\
            x.name for x in ServiceClass.objects.all().order_by('-name')]

        self.assertEquals(res_sclasnames, expected)

        # both name and order
        filter_order = filter_order_t.format(
            'name_contains: "er"',
            'name_ASC'
        )

        query = query_t.format(filter_order=filter_order)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        edges = result.data['services_classes']['edges']
        res_sclasnames = [ x['node']['name'] for x in edges ]
        expected = ['Internal', 'External', 'Ethernet']

        self.assertEquals(res_sclasnames, expected)
