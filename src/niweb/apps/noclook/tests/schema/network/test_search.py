# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import logging
from graphene import relay
from niweb.schema import schema
from pprint import pformat
from apps.noclook.models import NodeHandle, NodeType
from . import Neo4jGraphQLNetworkTest

class SearchPortTest(Neo4jGraphQLNetworkTest):
    def test_search_port(self):
        port_name = '404'

        query = '''
        {{
          search_port(filter:{{ query: "{port_name}" }}){{
            edges{{
              node{{
                id
                name
                description
              }}
            }}
          }}
        }}
        '''.format(port_name=port_name)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
