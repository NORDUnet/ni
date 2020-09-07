# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.schema.query import NOCRootQuery, \
                                        network_org_types, host_owner_types, \
                                        optical_path_dependency_types
from niweb.schema import schema
from graphene import relay
from . import Neo4jGraphQLNetworkTest

import random

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
