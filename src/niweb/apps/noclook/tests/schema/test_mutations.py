# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from collections import OrderedDict
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLTest

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
                            ('handle_id', '17'),
                            ('name', 'New test group')
                        ])),
                    ('clientMutationId', None)
                ])
            )
        ])

        result = schema.execute(query, context=self.context)

        assert not result.errors, result.errors
        assert result.data == expected

        ## update ##
        query = """
        mutation update_test_group {
          update_group(input: {handle_id: 17, name: "A test group"}){
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
                            ('handle_id', '17'),
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
            success
          }
        }
        """

        expected = OrderedDict([
            ('delete_group',
                OrderedDict([
                    ('success', True),
                ])
            )
        ])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected
