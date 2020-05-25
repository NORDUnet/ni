# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import logging
from graphene import relay
from niweb.schema import schema
from pprint import pformat
from apps.noclook.models import NodeHandle, NodeType
from apps.noclook.tests.stressload.data_generator import NetworkFakeDataGenerator
from . import Neo4jGraphQLNetworkTest

class SearchPortTest(Neo4jGraphQLNetworkTest):
    def test_search_port(self):
        data_generator = NetworkFakeDataGenerator()

        # get one of the ports
        common = 'test-0'
        port1 = data_generator.create_port(port_name="{}1".format(common))
        port2 = data_generator.create_port(port_name="{}2".format(common))

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
