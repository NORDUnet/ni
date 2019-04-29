# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from . import Neo4jGraphQLTest
from niweb.schema import schema

class QueryTest(Neo4jGraphQLTest):
    def test_get_contacts(self):
        query = '''
        mutation create_test_role {
          create_role(input: {name: "New test role"}){
            nodehandle {
              id
              name
            }
            clientMutationId
          }
        }
        '''

        result = schema.execute(query)
        assert not result.errors
