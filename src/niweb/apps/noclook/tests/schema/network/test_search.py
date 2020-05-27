# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import logging
from graphene import relay
from niweb.schema import schema
from pprint import pformat
from apps.noclook.models import NodeHandle, NodeType
from apps.noclook.tests.stressload.data_generator import \
    CommunityFakeDataGenerator, NetworkFakeDataGenerator
from . import Neo4jGraphQLNetworkTest


class GlobalSearchTest(Neo4jGraphQLNetworkTest):
    def test_global_search(self):
        community_generator = CommunityFakeDataGenerator()
        network_generator = NetworkFakeDataGenerator()

        # create several entities
        organization1 = community_generator.create_organization(name="organization-01")
        organization2 = community_generator.create_organization(name="organization-02")

        port1 = network_generator.create_port(name="port-01")
        port2 = network_generator.create_port(name="port-02")

        # search common pattern
        query = '''
        {
          search_ninode(filter:{query: "-0"}){
            edges{
              node{
                id
                name
                __typename
              }
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        results = result.data['search_ninode']['edges']
        print(NodeHandle.objects.all())
        self.assertEqual(len(results), 4)

        # search first pattern
        query = '''
        {
          search_ninode(filter:{query: "-01"}){
            edges{
              node{
                id
                name
                __typename
              }
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        results = result.data['search_ninode']['edges']
        self.assertEqual(len(results), 2)

        # search second pattern
        query = '''
        {
          search_ninode(filter:{query: "-02"}){
            edges{
              node{
                id
                name
                __typename
              }
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        results = result.data['search_ninode']['edges']
        self.assertEqual(len(results), 2)


class SearchPortTest(Neo4jGraphQLNetworkTest):
    def test_search_port(self):
        data_generator = NetworkFakeDataGenerator()

        # get one of the ports
        common = 'test-0'
        port1 = data_generator.create_port(name="{}1".format(common))
        port2 = data_generator.create_port(name="{}2".format(common))

        # search common pattern
        search = common
        query = '''
        {{
          search_port(filter:{{ query: "{search}" }}){{
            edges{{
              node{{
                id
                name
                description
              }}
            }}
          }}
        }}
        '''.format(search=search)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        results = result.data['search_port']['edges']
        self.assertEqual(len(results), 2)

        # search one port
        search = port1.node_name
        query = '''
        {{
          search_port(filter:{{ query: "{search}" }}){{
            edges{{
              node{{
                id
                name
                description
              }}
            }}
          }}
        }}
        '''.format(search=search)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        results = result.data['search_port']['edges']
        self.assertEqual(len(results), 1)
