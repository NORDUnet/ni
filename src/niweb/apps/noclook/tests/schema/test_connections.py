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
                type
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
                             'university_coldep')]))]),
                         OrderedDict([('node',
                           OrderedDict([('node_name',
                             'organization1'),
                            ('type',
                             'university_college')]))])])]))])

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
                node_name
                type
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
                           ('type',
                            'university_college')]))]),
                        OrderedDict([('node',
                           OrderedDict([('node_name',
                             'organization2'),
                            ('type',
                             'university_coldep')]))]),
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
