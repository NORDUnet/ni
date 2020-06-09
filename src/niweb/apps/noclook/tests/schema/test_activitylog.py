# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest
from apps.noclook.models import Context
from collections import OrderedDict
from graphene import relay
from niweb.schema import schema
from pprint import pformat

class ActivitylogTest(Neo4jGraphQLGenericTest):
    def query_activity(self, contextname):
        query = '''
        {{
          getContextActivity(filter: {{ context: "{contextname}" }}){{
            edges{{
              node{{
                text
                actorname
                actor{{
                  id
                  username
                  first_name
                  last_name
                  email
                }}
                verb
                action_object{{
                  id
                  name
                  __typename
                }}
                target_object{{
                  id
                  name
                  __typename
                }}
                description
              }}
            }}
          }}
        }}
        '''.format(contextname=contextname)
        result = schema.execute(query, context=self.context)

        return result


class Neo4jGraphQLActivitylogTest(ActivitylogTest):
    def test_crud(self):
        ## check available contexts/modules
        query ='''
        {
          getAvailableContexts
        }
        '''
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = {
            'getAvailableContexts': [x.name for x in Context.objects.all()]
        }

        self.assertEqual(result.data, expected)

        ## activity tests
        # create a node (group)
        query = '''
        mutation{
          create_group(input:{
            name: "Test group"
            description: "Lorem ipsum dolor sit amet"
          }){
            errors{
              field
              messages
            }
            group{
              id
              name
              description
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        assert not result.data['create_group']['errors'], \
            pformat(result.data['create_group']['errors'], indent=1)

        group_id = result.data['create_group']['group']['id']

        # check activity
        result = self.query_activity('Community')
        assert not result.errors, pformat(result.errors, indent=1)

        # check result length
        result_actions = result.data['getContextActivity']['edges']

        self.assertTrue(len(result_actions) == 1)
        result_action = result_actions[0]['node']

        # check action verb
        self.assertEqual(result_action['verb'], 'create')

        # check actor name
        self.assertEqual(result_action['actorname'], self.user.username)

        # check actor id as we have admin rights over Community
        result_user = result_action['actor']
        self.assertEqual(int(result_user['id']), self.user.id)

        # check action object (only its id)
        test_group_id = result_action['action_object']['id']
        self.assertEqual(test_group_id, group_id)

        # edit a node
        query = '''
        mutation{{
          update_group(input:{{
            id: "{group_id}"
            name: "Check group"
            description: "Lorem ipsum dolor sit amet"
          }}){{
            errors{{
              field
              messages
            }}
            group{{
              id
              name
              description
            }}
          }}
        }}
        '''.format(group_id=group_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        assert not result.data['update_group']['errors'], \
            pformat(result.data['update_group']['errors'], indent=1)

        # check activity
        result = self.query_activity('Community')
        assert not result.errors, pformat(result.errors, indent=1)

        ## check result length
        result_actions = result.data['getContextActivity']['edges']
        self.assertTrue(len(result_actions) == 2)

        result_action = result_actions[0]['node']

        # check action verb
        self.assertEqual(result_action['verb'], 'update')

        # check actor name
        self.assertEqual(result_action['actorname'], self.user.username)

        # check action object (only its id)
        test_group_id = result_action['action_object']['id']
        self.assertEqual(test_group_id, group_id)

        # delete a node
        query = '''
        mutation{{
          delete_group(input:{{
            id: "{group_id}"
          }}){{
            errors{{
              field
              messages
            }}
            success
          }}
        }}
        '''.format(group_id=group_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check activity
        result = self.query_activity('Community')
        assert not result.errors, pformat(result.errors, indent=1)

        ## check result length
        result_actions = result.data['getContextActivity']['edges']

        self.assertTrue(len(result_actions) == 1)

        result_action = result_actions[0]['node']

        # check action verb
        self.assertEqual(result_action['verb'], 'delete')

        # check actor name
        self.assertEqual(result_action['actorname'], self.user.username)

        # check action_object
        self.assertEqual(result_action['action_object'], None)


class Neo4jGraphQLActivitylogPermissionTest(ActivitylogTest):
    def setUp(self, group_dict=None):
        group_dict = {
            'community': {
                'admin': False,
                'read': True,
                'list': True,
                'write': True,
            },
            'network': {
                'admin': True,
                'read': False,
                'list': False,
                'write': True,
            }
        }

        super(Neo4jGraphQLActivitylogPermissionTest, self).setUp(group_dict=group_dict)


    def test_permissions(self):
        ## permissions
        ## check a node that the user is not allowed to read
        # create a node (end user)
        query = '''
        mutation{
          create_endUser(input:{
            name: "Test",
            description: "Lorem ipsum"
            url: "https://sunet.se"
          }){
            errors{
              field
              messages
            }
            endUser{
              id
              name
              description
              url
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        assert not result.data['create_endUser']['errors'], \
            pformat(result.data['create_endUser']['errors'], indent=1)

        # check activity
        result = self.query_activity('Network')
        assert not result.errors, pformat(result.errors, indent=1)

        ## check result length
        ## (should be zero as we don't have network list and read rights)
        result_actions = result.data['getContextActivity']['edges']
        self.assertTrue(len(result_actions) == 0)

        ## check the actor object for a node without the right admin permission
        # create a node (group)
        query = '''
        mutation{
          create_group(input:{
            name: "Test group"
            description: "Lorem ipsum dolor sit amet"
          }){
            errors{
              field
              messages
            }
            group{
              id
              name
              description
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        assert not result.data['create_group']['errors'], \
            pformat(result.data['create_group']['errors'], indent=1)

        # check activity
        result = self.query_activity('Community')
        assert not result.errors, pformat(result.errors, indent=1)

        ## check result length
        ## (should be one as we have community list and read rights)
        result_actions = result.data['getContextActivity']['edges']
        self.assertTrue(len(result_actions) == 1)

        result_action = result_actions[0]['node']
        self.assertEqual(result_action['actor'], None)
