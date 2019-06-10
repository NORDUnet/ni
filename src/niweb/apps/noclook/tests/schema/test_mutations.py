# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from collections import OrderedDict
from . import Neo4jGraphQLTest
from niweb.schema import schema

class QueryTest(Neo4jGraphQLTest):
    def test_group(self):
        ## create ##
        query = '''
        mutation create_test_group {
          create_group(input: {name: "New test group"}){
            group {
              handle_id
              name
            }
            clientMutationId
          }
        }
        '''

        expected = OrderedDict([
            ('create_group',
                OrderedDict([
                    ('group',
                        OrderedDict([
                            ('handle_id', '9'),
                            ('name', 'New test group')
                        ])),
                    ('clientMutationId', None)
                ])
            )
        ])

        result = schema.execute(query, context=self.context)
        #from pprint import pformat
        #raise Exception(pformat(result.data))

        assert not result.errors, result.errors
        assert result.data == expected

        ## update ##
        query = """
        mutation update_test_group {
          update_group(input: {handle_id: 9, name: "A test group"}){
            group {
              handle_id
              name
            }
            clientMutationId
          }
        }
        """

        expected = OrderedDict([
            ('update_group',
                OrderedDict([
                    ('group',
                        OrderedDict([
                            ('handle_id', '9'),
                            ('name', 'A test group')
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
        mutation delete_test_group {
          delete_group(input: {handle_id: 9}){
            group{
              handle_id
            }
          }
        }
        """

        expected = OrderedDict([
            ('delete_group',
                OrderedDict([
                    ('group', None),
                ])
            )
        ])

        result = schema.execute(query, context=self.context)
        assert not result.errors
        assert result.data == expected
