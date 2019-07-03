# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from collections import OrderedDict
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLTest

class QueryTest(Neo4jGraphQLTest):
    def test_get_contacts(self):
        # test contacts
        query = '''
        query getLastTwoContacts {
          contacts(first: 2, orderBy: handle_id_DESC) {
            edges {
              node {
                name
                first_name
                last_name
                member_of_groups {
                  name
                }
                roles{
                  name
                }
              }
            }
          }
        }
        '''

        expected = OrderedDict([('contacts',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('name', 'John Smith'),
                            ('first_name', 'John'),
                            ('last_name', 'Smith'),
                            ('member_of_groups',
                             [OrderedDict([('name',
                                'group2')])]),
                            ('roles',
                             [OrderedDict([('name',
                                'role2')])])]))]),
                         OrderedDict([('node',
                           OrderedDict([('name', 'Jane Doe'),
                            ('first_name', 'Jane'),
                            ('last_name', 'Doe'),
                            ('member_of_groups',
                             [OrderedDict([('name',
                                'group1')])]),
                            ('roles',
                             [OrderedDict([('name',
                                'role1')])])]))])])]))])

        result = schema.execute(query, context=self.context)

        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        # subquery test
        query = '''
        query {
          contacts(filter: {AND: [
            {
              member_of_groups: { name: "group2" },
              roles: { name: "role2"}
            }
          ]}){
            edges{
              node{
                name
                roles{
                  name
                }
                member_of_groups{
                  name
                  handle_id
                }
              }
            }
          }
        }
        '''
        expected = OrderedDict([('contacts',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('name', 'John Smith'),
                            ('roles',
                             [OrderedDict([('name',
                                'role2')])]),
                            ('member_of_groups',
                             [OrderedDict([('name',
                                'group2'),
                               ('handle_id',
                                '34')])])]))])])]))])


        result = schema.execute(query, context=self.context)

        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        query = '''
        query {
          contacts(orderBy: handle_id_DESC, filter: {AND: [
            {
              member_of_groups_in: [{ name: "group1" }, { name: "group2" }],
              roles_in: [{ name: "role1" }, { name: "role2" }]
            }
          ]}){
            edges{
              node{
                name
                member_of_groups{
                  name
                }
                roles{
                  name
                }
              }
            }
          }
        }
        '''
        expected = OrderedDict([('contacts',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('name', 'John Smith'),
                            ('member_of_groups',
                             [OrderedDict([('name',
                                'group2')])]),
                            ('roles',
                             [OrderedDict([('name',
                                'role2')])])]))]),
                         OrderedDict([('node',
                           OrderedDict([('name', 'Jane Doe'),
                            ('member_of_groups',
                             [OrderedDict([('name',
                                'group1')])]),
                            ('roles',
                             [OrderedDict([('name',
                                'role1')])])]))])])]))])

        result = schema.execute(query, context=self.context)

        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        query = '''
        query {
          contacts(filter: {AND: [
            {
              member_of_groups: { name: "group2" },
              roles: { name: "role2" }
            }
          ]}){
            edges{
              node{
                handle_id
                name
                roles{
                  name
                }
                member_of_groups{
                  name
                  handle_id
                }
              }
            }
          }
        }
        '''
        expected = OrderedDict([('contacts',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('handle_id', '30'),
                            ('name', 'John Smith'),
                            ('roles',
                             [OrderedDict([('name',
                                'role2')])]),
                            ('member_of_groups',
                             [OrderedDict([('name',
                                'group2'),
                               ('handle_id',
                                '34')])])]))])])]))])


        result = schema.execute(query, context=self.context)

        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        # getNodeById
        query = '''
        query {
          getNodeById(handle_id: 30){
            handle_id
          }
        }
        '''

        expected = OrderedDict([
                    ('getNodeById', OrderedDict([('handle_id', '30')]))
                ])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        # filter tests
        query = '''
        {
          groups(first: 10, filter:{
            AND:[{
              name: "group1", name_not: "group2",
              name_not_in: ["group2"]
            }]
          }, orderBy: handle_id_ASC){
            edges{
              node{
                name
              }
            }
          }
        }
        '''
        expected = OrderedDict([('groups',
                        OrderedDict([('edges',
                            [OrderedDict([('node',
                                   OrderedDict([('name',
                                         'group1')]
                                    ))])]
                            )]))
                    ])


        result = schema.execute(query, context=self.context)

        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        query = '''
        {
          groups(first: 10, filter:{
            OR:[{
              name_in: ["group1", "group2"]
            },{
              name: "group2",
            }]
          }, orderBy: handle_id_ASC){
            edges{
              node{
                name
              }
            }
          }
        }
        '''
        expected = OrderedDict([('groups',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('name', 'group1')]))]),
                         OrderedDict([('node',
                           OrderedDict([('name',
                                 'group2')]))])])]))])

        result = schema.execute(query, context=self.context)

        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

    def test_dropdown(self):
        query = '''
        {
          getAvailableDropdowns
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert 'contact_type' in result.data['getAvailableDropdowns'], pformat(result.data, indent=1)

        query = '''
        query{
          getChoicesForDropdown(name:"contact_type"){
            name
            value
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
