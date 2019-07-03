# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from collections import OrderedDict
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLTest

class QueryTest(Neo4jGraphQLTest):
    def test_group(self):
        ### Simple entity ###
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

        ### Composite entities ###
        ## create ##
        query = """
        mutation create_test_contact {
          create_contact(
            input: {
              first_name: "Jane"
              last_name: "Smith"
              title: ""
              salutation: "Ms"
              contact_type: "person"
              phone: "	823-971-5606"
              mobile: "617-372-0822"
              email: "jsmith@mashable.com"
              other_email: "jsmith1@mashable.com"
            }
          ){
            contact{
              handle_id
              name
              first_name
              last_name
              title
              salutation
              contact_type
              phone
              mobile
              email
              other_email
            }
          }
        }
        """

        expected = OrderedDict([('create_contact',
                      OrderedDict([('contact',
                        OrderedDict([('handle_id', '18'),
                                     ('name', 'Jane Smith'),
                                     ('first_name', 'Jane'),
                                     ('last_name', 'Smith'),
                                     ('title', None),
                                     ('salutation', 'Ms'),
                                     ('contact_type', 'person'),
                                     ('phone', '823-971-5606'),
                                     ('mobile', '617-372-0822'),
                                     ('email', 'jsmith@mashable.com'),
                                     ('other_email',
                                      'jsmith1@mashable.com')]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        ## update ##
        query = """
        mutation update_test_contact {
          update_contact(
            input: {
              handle_id: 18
              first_name: "Janet"
              last_name: "Doe"
              contact_type: "person"
              relationship_works_for: 10
              role_name: "IT-manager"
            }
          ){
            contact{
              handle_id
              name
              first_name
              last_name
              title
              salutation
              contact_type
              phone
              mobile
              email
              other_email
              roles{
                name
                end_node{
                  handle_id
                  name
                }
              }
            }
          }
        }
        """

        expected = OrderedDict([('update_contact',
              OrderedDict([('contact',
                            OrderedDict([('handle_id', '18'),
                                         ('name', 'Janet Doe'),
                                         ('first_name', 'Janet'),
                                         ('last_name', 'Doe'),
                                         ('title', None),
                                         ('salutation', None),
                                         ('contact_type', 'person'),
                                         ('phone', None),
                                         ('mobile', None),
                                         ('email', None),
                                         ('other_email', None),
                                         ('roles',
                                          [OrderedDict([
                                                        ('name', 'IT-manager'),
                                                        ('end_node',
                                                         OrderedDict([('handle_id',
                                                                       '10'),
                                                                      ('name',
                                                                       'organization2')]))])])]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        ## delete ##
        query = """
        mutation delete_test_contact {
          delete_contact(input: {handle_id: 18}){
            success
          }
        }
        """

        expected = OrderedDict([
            ('delete_contact',
                OrderedDict([
                    ('success', True),
                ])
            )
        ])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)
