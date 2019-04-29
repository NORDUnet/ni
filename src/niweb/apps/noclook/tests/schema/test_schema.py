# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from collections import OrderedDict
from . import Neo4jGraphQLTest
from niweb.schema import schema

class QueryTest(Neo4jGraphQLTest):
    def test_get_contacts(self):
        query = '''
        query getLastTenContacts {
          contacts(limit: 10) {
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
        '''

        expected = {
            'contacts': [
                OrderedDict([
                    ('handle_id', '13'),
                    ('name', 'John Smith'),
                    ('first_name', 'John'),
                    ('last_name', 'Smith'),
                    ('is_roles', [OrderedDict([('name', 'role2')])]),
                    ('member_of_groups', [OrderedDict([('name', 'group2')])]),
                ]),
                OrderedDict([
                    ('handle_id', '12'),
                    ('name', 'Jane Doe'),
                    ('first_name', 'Jane'),
                    ('last_name', 'Doe'),
                    ('is_roles', [OrderedDict([('name', 'role1')])]),
                    ('member_of_groups', [OrderedDict([('name', 'group1')])]),
                ]),
            ]
        }
        result = schema.execute(query)

        assert not result.errors
        assert result.data == expected
