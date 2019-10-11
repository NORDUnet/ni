# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from collections import OrderedDict
from . import Neo4jGraphQLTest
from niweb.schema import schema

class ConnectionTest(Neo4jGraphQLTest):
    def test_filter(self):
        ## create ##
        query = '''
        {
        	groups(filter: {AND: [
            {
              name: "group1"
            }
          ]}){
            edges{
              node{
                handle_id
                name
                outgoing {
                  name
                  relation {
                    id
                  }
                }
              }
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
