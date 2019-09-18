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
        group_handle_id = int(result.data['groups']['edges'][0]['node']['handle_id'])

        expected = OrderedDict([
            ('create_group',
                OrderedDict([
                    ('group',
                        OrderedDict([
                            ('handle_id', str(group_handle_id)),
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
        """.format(handle_id=group_handle_id)

        expected = OrderedDict([
            ('update_group',
                OrderedDict([
                    ('group',
                        OrderedDict([
                            ('handle_id', str(group_handle_id)),
                            ('name', 'A test group')
                        ])),
                    ('clientMutationId', None)
                ])
            )
        ])

        result = schema.execute(query, context=self.context)

        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected , pformat(result.data, indent=1)

        ## delete ##
        query = """
        mutation delete_test_group {{
          delete_group(input: {{ handle_id: {handle_id} }}){{
            success
          }}
        }}
        """.format(handle_id=group_handle_id)

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

        ### Composite entities (Contact) ###
        # get the first organization
        query= """
        {
          organizations(orderBy: handle_id_ASC, first: 1) {
            edges {
              node {
                handle_id
              }
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        organization_id = result.data['organizations']['edges'][0]['node']['handle_id']
        organization_id = int(organization_id)

        # get the first group
        # query the api to get the handle_id of the new group
        query= """
        {
          groups(orderBy: handle_id_ASC, first: 1) {
            edges {
              node {
                handle_id
              }
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        group_handle_id = result.data['groups']['edges'][0]['node']['handle_id']
        group_handle_id = int(group_handle_id)

        # get IT-manager role
        query = '''
        {
          roles(filter: {name: "NOC Manager"}){
            edges{
              node{
                handle_id
                name
              }
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        role_handle_id = result.data['roles']['edges'][0]['node']['handle_id']

        ## create ##
        note_txt = "Lorem ipsum dolor sit amet"

        query = """
        mutation create_test_contact {{
          create_contact(
            input: {{
              first_name: "Jane"
              last_name: "Smith"
              title: ""
              contact_type: "person"
              phone: "	823-971-5606"
              mobile: "617-372-0822"
              email: "jsmith@mashable.com"
              other_email: "jsmith1@mashable.com"
              relationship_works_for: {organization_id}
              role: {role_handle_id}
              relationship_member_of: {group_handle_id}
              notes: "{note_txt}"
            }}
          ){{
            contact{{
              name
              first_name
              last_name
              title
              contact_type
              phone
              mobile
              email
              other_email
              notes
              roles{{
                name
                end{{
                  handle_id
                  node_name
                }}
              }}
              member_of_groups{{
                name
              }}
            }}
          }}
        }}
        """.format(organization_id=organization_id,
                    role_handle_id=role_handle_id, group_handle_id=group_handle_id,
                    note_txt=note_txt)

        expected = OrderedDict([('create_contact',
                      OrderedDict([('contact',
                        OrderedDict([('name', 'Jane Smith'),
                                     ('first_name', 'Jane'),
                                     ('last_name', 'Smith'),
                                     ('title', None),
                                     ('contact_type', 'person'),
                                     ('phone', '823-971-5606'),
                                     ('mobile', '617-372-0822'),
                                     ('email', 'jsmith@mashable.com'),
                                     ('other_email',
                                      'jsmith1@mashable.com'),
                                     ('notes', note_txt),
                                      ('roles',
                                       [OrderedDict([('name', 'NOC Manager'),
                                         ('end',
                                          OrderedDict([('handle_id',
                                            str(organization_id)),
                                           ('node_name',
                                            'organization1')]))])]),
                                      ('member_of_groups',
                                       [OrderedDict([('name',
                                          'group1')])])]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        ## update ##
        query = """
        mutation update_test_contact {{
          update_contact(
            input: {{
              handle_id: 14
              first_name: "Janet"
              last_name: "Doe"
              contact_type: "person"
              relationship_works_for: {organization_id}
              role: {role_handle_id}
              relationship_member_of: {group_handle_id}
            }}
          ){{
            contact{{
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
              roles{{
                name
                end{{
                  handle_id
                  node_name
                }}
              }}
              member_of_groups{{
                name
              }}
            }}
          }}
        }}
        """.format(organization_id=organization_id,
                    role_handle_id=role_handle_id, group_handle_id=group_handle_id)

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
                                          [OrderedDict([('name', 'NOC Manager'),
                                            ('end',
                                             OrderedDict([('handle_id',
                                               str(organization_id)),
                                              ('node_name',
                                               'organization1')]))])]),
                                         ('member_of_groups',
                                          [OrderedDict([('name',
                                             'group1')])])]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        # test error output
        query = '''
        mutation{
          update_contact(input:{
            handle_id: 14,
            first_name: "Janet"
            last_name: "Janet"
            contact_type: "doesnt_exists"
          }){
            contact{
              handle_id
              name
            }
            errors{
              field
              messages
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert 'errors' in result.data['update_contact'], pformat(result.data, indent=1)

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

        ### Composite entities (Organization) ###
        # get the first organization
        query= """
        {
          organizations(orderBy: handle_id_ASC, first: 1) {
            edges {
              node {
                handle_id
              }
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        organization_id = result.data['organizations']['edges'][0]['node']['handle_id']
        organization_id = int(organization_id)

        # get the first two contacts
        query= """
        {
          contacts(orderBy: handle_id_ASC, first: 2){
            edges{
              node{
                handle_id
              }
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        contact_1_id = result.data['contacts']['edges'][0]['node']['handle_id']
        contact_1_id = int(contact_1_id)
        contact_2_id = result.data['contacts']['edges'][1]['node']['handle_id']
        contact_2_id = int(contact_2_id)

        incident_management_info = "Nullam eleifend ultrices risus, ac dignissim sapien mollis id. Aenean ante nibh, pharetra ac accumsan eget, suscipit eget purus. Ut sit amet diam in arcu dapibus ultricies. Phasellus a consequat eros. Proin cursus commodo consequat. Fusce nisl metus, egestas eu blandit sit amet, condimentum vitae felis."

        query = """
        mutation{{
          create_organization(
            input: {{
              name: "Another org",
              description: "This is the description of the new organization",
              phone: "34600000000",
              website: "www.sunet.se"
              incident_management_info: "{incident_management_info}",
              relationship_parent_of: {organization_id},
              abuse_contact: {contact_1_id},
              primary_contact: {contact_2_id},
              secondary_contact: {contact_1_id},
              it_technical_contact: {contact_2_id},
              it_security_contact: {contact_1_id},
              it_manager_contact: {contact_2_id}
            }}
          ){{
            organization{{
              name
              description
              phone
              website
              incident_management_info
            }}
          }}
        }}
        """.format(organization_id=organization_id,
                    contact_1_id=contact_1_id, contact_2_id=contact_2_id,
                    incident_management_info=incident_management_info)

        expected = OrderedDict([('create_organization',
              OrderedDict([('organization',
                            OrderedDict([('name', 'Another org'),
                                         ('description',
                                          'This is the description of the new '
                                          'organization'),
                                         ('phone', '34600000000'),
                                         ('website', 'www.sunet.se'),
                                         ('incident_management_info',
                                          incident_management_info)]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        ### Phone/Email tests ###
        phone_num = "+34600666006"
        phone_type = "work"
        query = """
        mutation{{
        	create_phone(input:{{
            type: "{phone_type}",
            name: "{phone_num}",
            contact: {contact_id}
          }}){{
            errors{{
              field
              messages
            }}
            phone{{
              name
              type
            }}
          }}
        }}
        """.format(phone_type=phone_type, phone_num=phone_num,
                    contact_id=contact_1_id)

        expected = OrderedDict([('create_phone',
                      OrderedDict([('errors', None),
                                   ('phone',
                                    OrderedDict([('name', phone_num),
                                                 ('type', phone_type)]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        ### Comments tests ###

        ## create ##
        query = """
        mutation{{
          create_comment(
            input:{{
              object_pk: {organization_id},
              comment: "This comment was added using the graphql api"
            }}
          ){{
            comment{{
              object_pk
              comment
              is_public
            }}
          }}
        }}
        """.format(organization_id=organization_id)

        expected =  OrderedDict([('create_comment',
              OrderedDict([('comment',
                            OrderedDict([('object_pk', str(organization_id)),
                                         ('comment',
                                          'This comment was added using the '
                                          'graphql api'),
                                         ('is_public', True)]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        ## read ##
        query = """
        {{
          getOrganizationById(handle_id: {organization_id}){{
            comments{{
              id
              comment
            }}
          }}
        }}
        """.format(organization_id=organization_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        comment_id = result.data['getOrganizationById']['comments'][0]['id']

        ## update ##
        query = """
        mutation{{
          update_comment(
            input:{{
              id: {comment_id},
              comment: "This comment was added using SRI's graphql api"
            }}
          ){{
            comment{{
              id
              comment
              is_public
            }}
          }}
        }}
        """.format(comment_id=comment_id)

        expected = OrderedDict([('update_comment',
              OrderedDict([('comment',
                            OrderedDict([('id', comment_id),
                                         ('comment',
                                          'This comment was added using SRI\'s '
                                          'graphql api'),
                                         ('is_public', True)]))]))])


        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        ## delete ##
        query = """
        mutation{{
          delete_comment(input:{{
            id: {comment_id}
          }}){{
            success
            id
          }}
        }}
        """.format(comment_id=comment_id)

        expected = OrderedDict([
            ('delete_comment',
                OrderedDict([('success', True), ('id', int(comment_id))])
            )
        ])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)
