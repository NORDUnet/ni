# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from collections import OrderedDict
from . import Neo4jGraphQLTest
from niweb.schema import schema

class QueryTest(Neo4jGraphQLTest):
    def test_role(self):
        ## create ##
        query = '''
        mutation create_test_role {
          create_role(input: {name: "New test role"}){
            nodehandle {
              handle_id
              name
            }
            clientMutationId
          }
        }
        '''

        expected = OrderedDict([
            ('create_role',
                OrderedDict([
                    ('nodehandle',
                        OrderedDict([
                            ('handle_id', '9'),
                            ('name', 'New test role')
                        ])),
                    ('clientMutationId', None)
                ])
            )
        ])

        result = schema.execute(query, context=self.context)

        assert not result.errors, result.errors
        assert result.data == expected

        ## update ##
        role_handle_id = int(result.data['create_role']['nodehandle']['handle_id'])
        query = """
        mutation update_test_role {
          update_role(input: {handle_id: 9, name: "A test role"}){
            nodehandle {
              handle_id
              name
            }
            clientMutationId
          }
        }
        """

        expected = OrderedDict([
            ('update_role',
                OrderedDict([
                    ('nodehandle',
                        OrderedDict([
                            ('handle_id', '9'),
                            ('name', 'A test role')
                        ])),
                    ('clientMutationId', None)
                ])
            )
        ])

        result = schema.execute(query, context=self.context)
        assert not result.errors
        assert result.data == expected

        ## delete ##
        query = """
        mutation delete_test_role {
          delete_role(input: {handle_id: 9}){
            nodehandle
          }
        }
        """

        expected = OrderedDict([
            ('delete_role',
                OrderedDict([
                    ('nodehandle', True),
                ])
            )
        ])

        result = schema.execute(query, context=self.context)
        assert not result.errors
        assert result.data == expected
