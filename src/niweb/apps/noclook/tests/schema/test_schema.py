# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle
from collections import OrderedDict
from django.utils.dateparse import parse_datetime
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLTest

from datetime import datetime

class QueryTest(Neo4jGraphQLTest):
    def test_get_contacts(self):
        # test contacts: slicing and ordering
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

        # AND filter with subentities
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
                                'group2')])])]))])])]))])


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
                name
                roles{
                  name
                }
                member_of_groups{
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
                           OrderedDict([
                            ('name', 'John Smith'),
                            ('roles',
                             [OrderedDict([('name',
                                'role2')])]),
                            ('member_of_groups',
                             [OrderedDict([('name',
                                'group2')])])]))])])]))])


        result = schema.execute(query, context=self.context)

        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        # filter by ScalarChoice
        query = '''
        {
          getAvailableDropdowns
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert 'organization_types' in result.data['getAvailableDropdowns'], pformat(result.data, indent=1)

        query = '''
        {
          getChoicesForDropdown(name: "organization_types"){
            name
            value
          }
        }
        '''
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        found = False
        for pair in result.data['getChoicesForDropdown']:
            if pair['value'] == 'provider':
                found = True
                break

        assert found, pformat(result.data, indent=1)

        query = '''
        {
        	organizations(filter:{
            AND: [
              { type: "provider" }
            ]
          }){
            edges{
              node{
                name
                type
              }
            }
          }
        }
        '''

        expected = OrderedDict([('organizations',
                    OrderedDict([('edges',
                        [OrderedDict([('node',
                            OrderedDict([
                                ('name',
                                 'organization1'),
                                ('type',
                                 'provider')]))])])]))])

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

        # test date and user filters

        # but first get the user and date
        query = '''
        {
        	groups(first:2){
            edges{
              node{
                handle_id
                node_name
                created
                modified
                creator{
                  username
                }
              }
            }
          }
        }
        '''
        result = schema.execute(query, context=self.context)

        node = result.data['groups']['edges'][0]['node']
        username = node['creator']['username']
        created = node['created']
        modified = node['modified']
        created_dt = parse_datetime(created)
        modified_dt = parse_datetime(modified)
        handle_id = int(node['handle_id'])

        # modify the second group to add an hour so it can be filtered
        node2 = result.data['groups']['edges'][1]['node']
        handle_id2 = int(node2['handle_id'])
        group2 = NodeHandle.objects.get(handle_id=handle_id2)

        query = '''
        {
        	groups(first:2){
            edges{
              node{
                handle_id
                node_name
                created
                modified
                creator{
                  username
                }
              }
            }
          }
        }
        '''
        result = schema.execute(query, context=self.context)

        node2 = result.data['groups']['edges'][1]['node']
        created2 = node2['created']
        modified2 = node2['modified']

        # test date filters: AND
        query = '''
        {{
          groups(first: 10, filter:{{
            AND:[{{
              created: "{adate}",
              created_in: ["{adate}"]
            }}]
          }}, orderBy: handle_id_ASC){{
            edges{{
              node{{
                name
              }}
            }}
          }}
        }}
        '''.format(adate=created, nodate=created2)
        expected = OrderedDict([('groups',
                        OrderedDict([('edges',
                            [OrderedDict([('node',
                                   OrderedDict([('name',
                                         'group1')]
                                    ))]),
                            OrderedDict([('node',
                                   OrderedDict([('name',
                                         'group2')]
                                    ))]),]
                            )]))
                    ])


        result = schema.execute(query, context=self.context)

        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        query = '''
        {{
          groups(first: 10, filter:{{
            AND:[{{
              modified: "{adate}",
              modified_in: ["{adate}"]
            }}]
          }}, orderBy: handle_id_ASC){{
            edges{{
              node{{
                name
              }}
            }}
          }}
        }}
        '''.format(adate=created)

        result = schema.execute(query, context=self.context)

        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        # test date filters: OR
        query = '''
        {{
          groups(first: 10, filter:{{
            OR:[{{
              created: "{adate}",
              created_in: ["{adate}"]
            }}]
          }}, orderBy: handle_id_ASC){{
            edges{{
              node{{
                name
              }}
            }}
          }}
        }}
        '''.format(adate=created)

        result = schema.execute(query, context=self.context)

        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        query = '''
        {{
          groups(first: 10, filter:{{
            OR:[{{
              modified: "{adate}",
              modified_in: ["{adate}"]
            }}]
          }}, orderBy: handle_id_ASC){{
            edges{{
              node{{
                name
              }}
            }}
          }}
        }}
        '''.format(adate=created)

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
