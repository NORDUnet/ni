# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from graphene import relay
from niweb.schema import schema
from pprint import pformat
from apps.noclook.models import NodeHandle, NodeType
from apps.noclook.tests.stressload.data_generator import \
    CommunityFakeDataGenerator, NetworkFakeDataGenerator
from . import Neo4jGraphQLNetworkTest

import logging
import norduniclient as nc


class GlobalSearchTest(Neo4jGraphQLNetworkTest):
    def get_expected_length(self, search):
        q = """
            MATCH (n:Node)
            WHERE any(prop in keys(n) WHERE n[prop] =~ "(?i).*{search}.*")
            RETURN count(n) as total
            """.format(search=search)

        res = nc.query_to_dict(nc.graphdb.manager, q, search=search)

        return res['total']

    def test_global_search(self):
        community_generator = CommunityFakeDataGenerator()
        network_generator = NetworkFakeDataGenerator()

        # create several entities
        organization1 = community_generator.create_organization(name="organization-01")
        organization2 = community_generator.create_organization(name="organization-02")

        port1 = network_generator.create_port(name="port-01")
        port2 = network_generator.create_port(name="port-02")

        # search common pattern
        query_t = '''
        {{
          search_generalsearch(filter:{{query: "{search}"}}){{
            edges{{
              node{{
                ninode{{
                  id
                  name
                  __typename
                }}
                match_txt
              }}
            }}
          }}
        }}
        '''

        search = '-0'
        query = query_t.format(search=search)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        expected_num = self.get_expected_length(search)

        results = result.data['search_generalsearch']['edges']
        self.assertEqual(len(results), expected_num, \
            pformat(result.data, indent=1))

        # search first pattern
        search = '-01'
        query = query_t.format(search=search)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        expected_num = self.get_expected_length(search)
        results = result.data['search_generalsearch']['edges']
        self.assertEqual(len(results), expected_num, \
            pformat(result.data, indent=1))

        # search second pattern
        search = '-02'
        query = query_t.format(search=search)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check length
        expected_num = self.get_expected_length(search)
        results = result.data['search_generalsearch']['edges']
        self.assertEqual(len(results), expected_num)


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
