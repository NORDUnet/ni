# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from collections import OrderedDict
from pprint import pformat
from . import Neo4jGraphQLTest
from niweb.schema import schema

class OrganizationConnectionTest(Neo4jGraphQLTest):
    def test_organizations_order(self):
        ## order by name
        query = '''
        {
          organizations( orderBy:name_ASC ){
            edges{
              node{
                name
              }
            }
          }
        }
        '''

        expected = OrderedDict([('organizations',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('name',
                             'organization1')]))]),
                         OrderedDict([('node',
                           OrderedDict([('name',
                             'organization2')]))])])]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )

        query = '''
        {
          organizations( orderBy:name_DESC ){
            edges{
              node{
                name
              }
            }
          }
        }
        '''

        expected = OrderedDict([('organizations',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('name',
                             'organization2')]))]),
                         OrderedDict([('node',
                           OrderedDict([('name',
                             'organization1')]))])])]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )

        ## order by organization id
        query = '''
        {
          organizations(
            orderBy: organization_id_ASC
        	){
            edges{
              node{
                node_name
                organization_id
              }
            }
          }
        }
        '''

        expected = OrderedDict([('organizations',
                    OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('node_name',
                             'organization1'),
                            ('organization_id',
                             'ORG1')]))]),
                         OrderedDict([('node',
                           OrderedDict([('node_name',
                             'organization2'),
                            ('organization_id',
                                 'ORG2')]))])])]))])


        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )

        query = '''
        {
          organizations(
            orderBy: organization_id_DESC
        	){
            edges{
              node{
                node_name
                organization_id
              }
            }
          }
        }
        '''

        expected = OrderedDict([('organizations',
                    OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('node_name',
                             'organization2'),
                            ('organization_id',
                             'ORG2')]))]),
                         OrderedDict([('node',
                           OrderedDict([('node_name',
                             'organization1'),
                            ('organization_id',
                                 'ORG1')]))])])]))])


        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )

        ## order by type
        query = '''
        {
          organizations( orderBy: type_ASC ){
            edges{
              node{
                node_name
                type{
                  name
                  value
                }
              }
            }
          }
        }
        '''

        expected = OrderedDict([('organizations',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('node_name',
                             'organization2'),
                            ('type',
                             OrderedDict([('name',
                               'University, '
                               'College '
                               'dep'),
                              ('value',
                               'university_coldep')]))]))]),
                         OrderedDict([('node',
                           OrderedDict([('node_name',
                             'organization1'),
                            ('type',
                             OrderedDict([('name',
                               'University, '
                               'College'),
                              ('value',
                               'university_college')]))]))])])]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )

        query = '''
        {
          organizations( orderBy: type_DESC ){
            edges{
              node{
                name
                type{
                  name
                  value
                }
              }
            }
          }
        }
        '''

        expected = OrderedDict([('organizations',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('name',
                             'organization1'),
                            ('type',
                             OrderedDict([('name',
                               'University, '
                               'College'),
                              ('value',
                               'university_college')]))]))]),
                         OrderedDict([('node',
                           OrderedDict([('name',
                             'organization2'),
                            ('type',
                             OrderedDict([('name',
                               'University, '
                               'College '
                               'dep'),
                              ('value',
                               'university_coldep')]))]))])])]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )

    def test_organizations_filter(self):
        # filter by name
        query = '''
        {
          organizations(
            filter:{
              AND:[{
                name: "organization1"
              }]
            }
        	){
            edges{
              node{
                name
                type{
                  name
                  value
                }
              }
            }
          }
        }
        '''

        expected = OrderedDict([('organizations',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([('name',
                             'organization1'),
                            ('type',
                             OrderedDict([('name',
                               'University, '
                               'College'),
                              ('value',
                               'university_college')]))]))])])]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )

        # filter by organization_id
        query = '''
        {
          organizations(
            filter:{
              AND:[{
                organization_id: "ORG1"
              }]
            }
        	){
            edges{
              node{
                name
                type{
                  name
                  value
                }
              }
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )

        # filter by type
        query = '''
        {
          organizations(
            filter:{
              AND:[{
                type: "university_college"
              }]
            }
        	){
            edges{
              node{
                name
                type{
                  name
                  value
                }
              }
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )


class ContactConnectionTest(Neo4jGraphQLTest):
    def test_organizations_order(self):
        ## order by name
        query = '''
        {
          contacts( orderBy: name_ASC){
            edges{
              node{
                name
              }
            }
          }
        }
        '''

        expected = OrderedDict([('contacts',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                           OrderedDict([
                            ('name',
                             'Jane Doe')]))]),
                         OrderedDict([('node',
                           OrderedDict([
                            ('name',
                             'John '
                             'Smith')]))])])]))])


        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )

        query = '''
        {
          contacts( orderBy: name_DESC){
            edges{
              node{
                name
              }
            }
          }
        }
        '''

        expected = OrderedDict([('contacts',
                      OrderedDict([('edges',
                        [OrderedDict([('node',
                          OrderedDict([
                           ('name',
                            'John '
                            'Smith')]))]),
                        OrderedDict([('node',
                           OrderedDict([
                            ('name',
                             'Jane Doe')]))]),
                             ])]))])


        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )

        ## order by organization
        query = '''
        {
          contacts( orderBy: organizations_ASC){
            edges{
              node{
                name
                organizations{
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
                       OrderedDict([('name', 'Jane Doe'),
                        ('organizations',
                         [OrderedDict([('name',
                            'organization1')])])]))]),
                     OrderedDict([('node',
                       OrderedDict([('name', 'John Smith'),
                        ('organizations',
                         [OrderedDict([('name',
                            'organization2')])])]))])])]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )

        query = '''
        {
          contacts( orderBy: organizations_DESC){
            edges{
              node{
                name
                organizations{
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
                       ('organizations',
                        [OrderedDict([('name',
                           'organization2')])])]))]),
                    OrderedDict([('node',
                       OrderedDict([('name', 'Jane Doe'),
                        ('organizations',
                         [OrderedDict([('name',
                            'organization1')])])]))]),
                            ])]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, result.errors
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(expected, indent=1),
            pformat(result.data, indent=1)
        )


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
