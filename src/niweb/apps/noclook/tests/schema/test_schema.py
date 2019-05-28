# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from collections import OrderedDict
from . import Neo4jGraphQLTest
from niweb.schema import schema

class QueryTest(Neo4jGraphQLTest):
    def test_get_contacts(self):
        query = '''
        query getLastTenContacts {
          contacts(first: 10) {
            edges {
              node {
                handle_id
                name
                first_name
                last_name
                is_roles {
                  name
                }
                member_of_groups {
                  name
                }
              }
            }
          }
        }
        '''

        expected =  OrderedDict([('contacts',
                      OrderedDict([('edges',
                        [
                         OrderedDict([('node',
                           OrderedDict([('handle_id', '21'),
                                ('name', 'John Smith'),
                                ('first_name', 'John'),
                                ('last_name', 'Smith'),
                                ('is_roles',
                                 [OrderedDict([('name',
                                    'role2')])]),
                                ('member_of_groups',
                                 [OrderedDict([('name',
                                    'group2')])])]))]),
                        OrderedDict([('node',
                           OrderedDict([('handle_id', '20'),
                                ('name', 'Jane Doe'),
                                ('first_name', 'Jane'),
                                ('last_name', 'Doe'),
                                ('is_roles',
                                 [OrderedDict([('name',
                                    'role1')])]),
                                ('member_of_groups',
                                 [OrderedDict([('name',
                                    'group1')])])]))]),
                        ])]))])


        result = schema.execute(query, context=self.context)

        assert not result.errors, result.errors
        assert result.data == expected

        query = '''
        query {
          getNodeById(handle_id: 20){
            handle_id
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors

    def test_getnodebyhandle_id(self):
        query = '''
        query {
          getNodeById(handle_id: 1){
            handle_id
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        #assert not result.errors, result.errors

    def test_dropdown(self):
        query = '''
        query{
          getChoicesForDropdown(name:"contact_type"){
            id
            dropdown{
              id
              name
              choice_set{
                id
                dropdown {
                  id
                }
                name
                value
              }
            }
            name
            value
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
