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

        expected = {
            'create_role': [
                OrderedDict([
                    ('nodehandle',
                        OrderedDict([
                            ('handle_id', '9'),
                            ('name', 'New test role'),
                        ])),
                    ('clientMutationId', None),
                ]),
            ]
        }

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


        result = schema.execute(query)

        assert not result.errors
        assert result.data == expected

        ## update ##
        role_handle_id = int(result.data['create_role']['nodehandle']['handle_id'])
        query = """
        mutation update_test_role {
          update_role(input: {handle_id: 9, name: "A test role"}){
            nodehandle {
              id
              name
            }
            clientMutationId
          }
        }
        """

        result = schema.execute(query)
        assert not result.errors

        """## delete ##
        query = '''
        mutation create_test_role {
          delete_role(input: {handle_id: {}}){
            nodehandle
            clientMutationId
          }
        }
        '''.format(role_handle_id)

        result = schema.execute(query)
        import pprint
        raise Exception(pprint.pprint(result.data))
        assert not result.errors"""
