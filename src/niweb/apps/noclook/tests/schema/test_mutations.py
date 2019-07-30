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
        new_group_name = "New test group"
        query = '''
        mutation create_test_group {{
          create_group(input: {{name: "{new_group_name}"}}){{
            group {{
              handle_id
              name
            }}
            clientMutationId
          }}
        }}
        '''.format(new_group_name=new_group_name)

        result = schema.execute(query, context=self.context)

        assert not result.errors, pformat(result.errors, indent=1)
        create_group_result = result.data

        # query the api to get the handle_id of the new group
        query = '''
        query {{
          groups(filter:{{ AND:[{{ name: "{new_group_name}" }}]}}){{
            edges{{
              node{{
                handle_id
              }}
            }}
          }}
        }}
        '''.format(new_group_name=new_group_name)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        handle_id = int(result.data['groups']['edges'][0]['node']['handle_id'])

        expected = OrderedDict([
            ('create_group',
                OrderedDict([
                    ('group',
                        OrderedDict([
                            ('handle_id', str(handle_id)),
                            ('name', new_group_name)
                        ])),
                    ('clientMutationId', None)
                ])
            )
        ])
        assert create_group_result == expected, pformat(result.data, indent=1)

        ## update ##
        query = """
        mutation update_test_group {{
          update_group(input: {{ handle_id: {handle_id}, name: "A test group"}} ){{
            group {{
              handle_id
              name
            }}
            clientMutationId
          }}
        }}
        """.format(handle_id=handle_id)

        expected = OrderedDict([
            ('update_group',
                OrderedDict([
                    ('group',
                        OrderedDict([
                            ('handle_id', str(handle_id)),
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
        mutation delete_test_group {{
          delete_group(input: {{ handle_id: {handle_id} }}){{
            success
          }}
        }}
        """.format(handle_id=handle_id)

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
                        OrderedDict([('handle_id', '14'),
                                     ('name', 'Jane Smith'),
                                     ('first_name', 'Jane'),
                                     ('last_name', 'Smith'),
                                     ('title', None),
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
              handle_id: 14
              first_name: "Janet"
              last_name: "Doe"
              contact_type: "person"
              relationship_works_for: 10
              role_name: "IT-manager"
              relationship_member_of: 16
            }
          ){
            contact{
              handle_id
              name
              first_name
              last_name
              title
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
              member_of_groups{
                name
              }
            }
          }
        }
        """

        expected = OrderedDict([('update_contact',
              OrderedDict([('contact',
                            OrderedDict([('handle_id', '14'),
                                         ('name', 'Janet Doe'),
                                         ('first_name', 'Janet'),
                                         ('last_name', 'Doe'),
                                         ('title', None),
                                         ('contact_type', 'person'),
                                         ('phone', None),
                                         ('mobile', None),
                                         ('email', None),
                                         ('other_email', None),
                                         ('roles',
                                          [OrderedDict([('name', 'IT-manager'),
                                            ('end_node',
                                             OrderedDict([('handle_id',
                                               '10'),
                                              ('name',
                                               'organization2')]))])]),
                                         ('member_of_groups',
                                          [OrderedDict([('name',
                                             'group2')])])]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        ## delete ##
        query = """
        mutation delete_test_contact {
          delete_contact(input: {handle_id: 14}){
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
