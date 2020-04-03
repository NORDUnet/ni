# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from collections import OrderedDict
from graphene import relay
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLTest

class JWTTest(Neo4jGraphQLTest):
    def test_jwt_mutations(self):
        ### jwt mutations
        ## get token
        test_username="test user"
        query = '''
        mutation{{
          token_auth(input: {{ username: "{user}", password: "{password}" }}) {{
            token
          }}
        }}
        '''.format(user=test_username, password="test")
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        token = result.data['token_auth']['token']

        ## verify token
        query = '''
        mutation{{
          verify_token(input: {{ token: "{token}" }}) {{
            payload
          }}
        }}
        '''.format(token=token)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data['verify_token']['payload']['username'] == test_username, \
            "The username from the jwt token doesn't match"

        ## refresh token
        query = '''
        mutation{{
          refresh_token(input: {{ token: "{token}" }}) {{
            token
            payload
          }}
        }}
        '''.format(token=token)
        result = schema.execute(query, context=self.context)
        assert not result.errors, result.data['refresh_token']['payload']
        assert result.data['refresh_token']['payload']['username'] == test_username, \
            "The username from the jwt token doesn't match"
        assert result.data['refresh_token']['token'], result.data['refresh_token']['token']

class SingleTest(Neo4jGraphQLTest):
    def test_single_mutations(self):
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
                id
                name
              }}
            }}
          }}
        }}
        '''.format(new_group_name=new_group_name)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        group_handle_id = result.data['groups']['edges'][0]['node']['id']

        expected = OrderedDict([('groups',
                        OrderedDict([('edges',
                            [
                                OrderedDict([
                                    ('node', OrderedDict([
                                            ('id', group_handle_id),
                                            ('name', new_group_name)
                                        ]))
                                ])
                            ]
                        )])
                    )])

        assert result.data == expected, '{}\n!=\n{}'.format(
                    pformat(expected, indent=1), pformat(result.data, indent=1))

        ## update ##
        query = """
        mutation update_test_group {{
          update_group(input: {{ id: "{id}", name: "A test group"}} ){{
            group {{
              id
              name
            }}
            clientMutationId
          }}
        }}
        """.format(id=group_handle_id)

        expected = OrderedDict([
            ('update_group',
                OrderedDict([
                    ('group',
                        OrderedDict([
                            ('id', group_handle_id),
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
          delete_group(input: {{ id: "{id}" }}){{
            success
          }}
        }}
        """.format(id=group_handle_id)

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
                id
              }
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        organization_id = result.data['organizations']['edges'][0]['node']['id']

        # get the first group
        # query the api to get the handle_id of the new group
        query= """
        {
          groups(orderBy: handle_id_ASC, first: 1) {
            edges {
              node {
                id
              }
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        group_handle_id = result.data['groups']['edges'][0]['node']['id']

        # get IT-manager role
        query = '''
        {
          roles(filter: {name: "NOC Manager"}){
            edges{
              node{
                id
                name
              }
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        role_id = result.data['roles']['edges'][0]['node']['id']

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
              relationship_works_for: "{organization_id}"
              role: "{role_id}"
              relationship_member_of: "{group_handle_id}"
              notes: "{note_txt}"
            }}
          ){{
            errors{{
              field
              messages
            }}
            contact{{
              id
              name
              first_name
              last_name
              title
              contact_type
              notes
              roles{{
                name
                end{{
                  id
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
                    role_id=role_id, group_handle_id=group_handle_id,
                    note_txt=note_txt)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert not result.data['create_contact']['errors'], \
            pformat(result.data['create_contact']['errors'], indent=1)
        contact_id = result.data['create_contact']['contact']['id']
        expected = OrderedDict([('create_contact',
                      OrderedDict([('errors', None),
                      ('contact',
                        OrderedDict([('id', contact_id),
                                     ('name', 'Jane Smith'),
                                     ('first_name', 'Jane'),
                                     ('last_name', 'Smith'),
                                     ('title', None),
                                     ('contact_type', 'person'),
                                     ('notes', note_txt),
                                      ('roles',
                                       [OrderedDict([('name', 'NOC Manager'),
                                         ('end',
                                          OrderedDict([('id',
                                            str(organization_id)),
                                           ('node_name',
                                            'organization1')]))])]),
                                      ('member_of_groups',
                                       [OrderedDict([('name',
                                          'group1')])])]))]))])

        assert result.data == expected, pformat(result.data, indent=1)

        ## update ##
        query = """
        mutation update_test_contact {{
          update_contact(
            input: {{
              id: "{contact_id}"
              first_name: "Janet"
              last_name: "Doe"
              contact_type: "person"
              relationship_works_for: "{organization_id}"
              role: "{role_id}"
              relationship_member_of: "{group_handle_id}"
            }}
          ){{
            contact{{
              id
              name
              first_name
              last_name
              title
              contact_type
              roles{{
                name
                end{{
                  id
                  node_name
                }}
              }}
              member_of_groups{{
                name
              }}
            }}
          }}
        }}
        """.format(contact_id=contact_id, organization_id=organization_id,
                    role_id=role_id, group_handle_id=group_handle_id)

        expected = OrderedDict([('update_contact',
              OrderedDict([('contact',
                            OrderedDict([('id', contact_id),
                                         ('name', 'Janet Doe'),
                                         ('first_name', 'Janet'),
                                         ('last_name', 'Doe'),
                                         ('title', None),
                                         ('contact_type', 'person'),
                                         ('roles',
                                          [OrderedDict([('name', 'NOC Manager'),
                                            ('end',
                                             OrderedDict([('id',
                                               organization_id),
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
        mutation{{
          update_contact(input:{{
            id: "{contact_id}",
            first_name: "Janet"
            last_name: "Janet"
            contact_type: "doesnt_exists"
          }}){{
            contact{{
              id
              name
            }}
            errors{{
              field
              messages
            }}
          }}
        }}
        '''.format(contact_id=contact_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert 'errors' in result.data['update_contact'], pformat(result.data, indent=1)

        # test another erroneous form
        fake_org_id = relay.Node.to_global_id('Organization', "-1")
        query = '''
        mutation{{
          update_contact(input:{{
            id: "{contact_id}",
            first_name: "Janet"
            last_name: "Janet"
            contact_type: "person"
            relationship_works_for: "{organization_id}"
          }}){{
            contact{{
              id
              name
            }}
            errors{{
              field
              messages
            }}
          }}
        }}
        '''.format(contact_id=contact_id, organization_id=fake_org_id)
        result = schema.execute(query, context=self.context)
        assert 'errors' in result.data['update_contact'], pformat(result.data, indent=1)

        ## delete ##
        query = """
        mutation delete_test_contact {{
          delete_contact(input: {{ id: "{contact_id}" }}){{
            success
          }}
        }}
        """.format(contact_id=contact_id)

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

class MultipleEntityTest(Neo4jGraphQLTest):
    def test_multiple_entity_mutations(self):
        ### Composite entities (Organization) ###
        # get the first organization
        query= """
        {
          organizations(orderBy: handle_id_ASC, first: 1) {
            edges {
              node {
                id
              }
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        organization_id = result.data['organizations']['edges'][0]['node']['id']

        # get the first two contacts
        query= """
        {
          contacts(orderBy: handle_id_ASC, first: 2){
            edges{
              node{
                id
              }
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        contact_1_id = result.data['contacts']['edges'][0]['node']['id']
        contact_2_id = result.data['contacts']['edges'][1]['node']['id']

        assert contact_1_id != contact_2_id, 'The contact ids are equal'

        incident_management_info = "Nullam eleifend ultrices risus, ac dignissim sapien mollis id. Aenean ante nibh, pharetra ac accumsan eget, suscipit eget purus. Ut sit amet diam in arcu dapibus ultricies. Phasellus a consequat eros. Proin cursus commodo consequat. Fusce nisl metus, egestas eu blandit sit amet, condimentum vitae felis."
        website = "www.demo.org"
        organization_number = "1234A"

        query = """
        mutation{{
          create_organization(
            input: {{
              name: "Another org",
              description: "This is the description of the new organization",
              incident_management_info: "{incident_management_info}",
              relationship_parent_of: "{organization_id}",
              abuse_contact: "{contact_1_id}",
              primary_contact: "{contact_2_id}",
              secondary_contact: "{contact_1_id}",
              it_technical_contact: "{contact_2_id}",
              it_security_contact: "{contact_1_id}",
              it_manager_contact: "{contact_2_id}",
              affiliation_provider: true,
              affiliation_customer: true,
              website: "{website}",
              organization_number: "{organization_number}"
            }}
          ){{
            errors{{
              field
              messages
            }}
            organization{{
              id
              name
              description
              incident_management_info
              affiliation_provider
              affiliation_customer
              website
              organization_number
              incoming{{
                name
                relation{{
                  id
                  start{{
                    id
                    node_name
                  }}
                  end{{
                    id
                    node_name
                  }}
                }}
              }}
            }}
          }}
        }}
        """.format(organization_id=organization_id,
                    contact_1_id=contact_1_id, contact_2_id=contact_2_id,
                    incident_management_info=incident_management_info,
                    website=website, organization_number=organization_number)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        form_errors = result.data['create_organization']['errors']
        assert not form_errors, pformat(form_errors, indent=1)
        organization_id_2 = result.data['create_organization']['organization']['id']
        incoming_relations = result.data['create_organization']['organization']['incoming']

        expected = OrderedDict([('create_organization',
              OrderedDict([('errors', None),
                            ('organization',
                            OrderedDict([('id', organization_id_2),
                                         ('name', 'Another org'),
                                         ('description',
                                          'This is the description of the new '
                                          'organization'),
                                         ('incident_management_info',
                                          incident_management_info),
                                          ('affiliation_provider', True),
                                          ('affiliation_customer', True),
                                          ('website', website),
                                          ('organization_number', organization_number),
                                          ('incoming', incoming_relations)]))]))])

        found_offspring = False
        for relation in incoming_relations:
            for k, relation_dict in relation.items():
                if k == 'name' and relation_dict == 'Parent_of':
                    start_id = relay.Node.from_global_id(relation['relation']['start']['id'])[1]
                    org_id = relay.Node.from_global_id(organization_id)[1]

                    if start_id == org_id:
                        found_offspring = True

        assert found_offspring, pformat(result.data, indent=1)

        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '{}\n!=\n{}'.format(
            pformat(result.data, indent=1), pformat(expected, indent=1))

        ## edit organization
        query = """
        mutation{{
          update_organization(
            input: {{
              id: "{organization_id}"
              name: "Another org",
              description: "This is the description of the new organization",
              abuse_contact: "{contact_1_id}",
              primary_contact: "{contact_2_id}",
              secondary_contact: "{contact_1_id}",
              it_technical_contact: "{contact_2_id}",
              it_security_contact: "{contact_1_id}",
              it_manager_contact: "{contact_2_id}",
              affiliation_provider: false,
              affiliation_partner: true,
              website: "{website}",
              organization_number: "{organization_number}"
            }}
          ){{
            organization{{
              id
              name
              description
              incident_management_info
              affiliation_provider
              affiliation_partner
              affiliation_customer
              website
              organization_number
            }}
          }}
        }}
        """.format(organization_id=organization_id_2,
                    contact_1_id=contact_1_id, contact_2_id=contact_2_id,
                    website=website, organization_number=organization_number)

        expected = OrderedDict([('update_organization',
              OrderedDict([('organization',
                            OrderedDict([('id', organization_id_2),
                                         ('name', 'Another org'),
                                         ('description',
                                          'This is the description of the new '
                                          'organization'),
                                         ('incident_management_info',
                                          incident_management_info),
                                          ('affiliation_provider', False),
                                          ('affiliation_partner', True),
                                          ('affiliation_customer', True),
                                          ('website', website),
                                          ('organization_number', organization_number)]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

        ### Phone/Email tests ###

        ## create ##
        phone_num = "823-971-5606"
        phone_type = "work"
        query = """
          mutation{{
        	create_phone(input:{{
              type: "{phone_type}",
              name: "{phone_num}",
              contact: "{contact_id}"
            }}){{
              errors{{
                field
                messages
              }}
              phone{{
                id
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
                                    OrderedDict([('id', None),
                                                 ('name', phone_num),
                                                 ('type', phone_type)]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        phone_id_str = result.data['create_phone']['phone']['id']
        expected['create_phone']['phone']['id'] = phone_id_str

        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        ## read ##
        query = """
        {{
          getContactById(id: "{contact_id}"){{
            id
            phones{{
              id
              name
              type
            }}
          }}
        }}
        """.format(contact_id=contact_1_id)

        expected = OrderedDict([('getContactById',
                      OrderedDict([('id', contact_1_id),
                                   ('phones',
                                    [OrderedDict([('id', phone_id_str),
                                                  ('name', phone_num),
                                                  ('type', phone_type)])])]))])


        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        ## update ##
        new_phone_num = "617-372-0822"
        query = """
          mutation{{
        	update_phone(input:{{
              id: "{phone_id}"
              type: "{phone_type}",
              name: "{phone_num}",
              contact: "{contact_id}"
            }}){{
              errors{{
                field
                messages
              }}
              phone{{
                id
                name
                type
              }}
            }}
          }}
        """.format(phone_id=phone_id_str, phone_type=phone_type,
                    phone_num=new_phone_num, contact_id=contact_1_id)

        expected = OrderedDict([('update_phone',
                      OrderedDict([('errors', None),
                                   ('phone',
                                    OrderedDict([('id', phone_id_str),
                                                 ('name', new_phone_num),
                                                 ('type', phone_type)]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        ## delete ##
        query = """
        mutation{{
          delete_phone(input: {{
            id: "{phone_id}"
          }}){{
            errors{{
              field
              messages
            }}
            success
          }}
        }}
        """.format(phone_id=phone_id_str)

        expected = OrderedDict([('delete_phone',
                      OrderedDict([('errors', None),
                                   ('success', True)
                                   ]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        ## Email ##
        ## create ##
        email_str = "ssvensson@sunet.se"
        email_type = "work"
        query = """
          mutation{{
        	create_email(input:{{
              type: "{email_type}",
              name: "{email_str}",
              contact: "{contact_id}"
            }}){{
              errors{{
                field
                messages
              }}
              email{{
                id
                name
                type
              }}
            }}
          }}
        """.format(email_type=email_type, email_str=email_str,
                    contact_id=contact_1_id)

        expected = OrderedDict([('create_email',
                      OrderedDict([('errors', None),
                                   ('email',
                                    OrderedDict([('id', None),
                                                 ('name', email_str),
                                                 ('type', email_type)]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        email_id_str = result.data['create_email']['email']['id']
        expected['create_email']['email']['id'] = email_id_str

        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        ## read ##
        query = """
        {{
          getContactById(id: "{contact_id}"){{
            id
            emails{{
              id
              name
              type
            }}
          }}
        }}
        """.format(contact_id=contact_1_id)

        expected = OrderedDict([('getContactById',
                      OrderedDict([('id', str(contact_1_id)),
                                   ('emails',
                                    [OrderedDict([('id', email_id_str),
                                                  ('name', email_str),
                                                  ('type', email_type)])])]))])


        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        ## update ##
        new_email = "617-372-0822"
        query = """
          mutation{{
        	update_email(input:{{
              id: "{email_id}"
              type: "{email_type}",
              name: "{email_str}",
              contact: "{contact_id}"
            }}){{
              errors{{
                field
                messages
              }}
              email{{
                id
                name
                type
              }}
            }}
          }}
        """.format(email_id=email_id_str, email_type=email_type,
                    email_str=new_email, contact_id=contact_1_id)

        expected = OrderedDict([('update_email',
                      OrderedDict([('errors', None),
                                   ('email',
                                    OrderedDict([('id', email_id_str),
                                                 ('name', new_email),
                                                 ('type', email_type)]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        ## delete ##
        query = """
        mutation{{
          delete_email(input: {{
            id: "{email_id}"
          }}){{
            errors{{
              field
              messages
            }}
            success
          }}
        }}
        """.format(email_id=email_id_str)

        expected = OrderedDict([('delete_email',
                      OrderedDict([('errors', None),
                                   ('success', True)
                                   ]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        ## Address ##
        ## create ##
        address_name = "New address"
        address_website = "emergya.com"
        address_phone = "617-372-0822"
        address_street = "Fake st 123"
        address_postal_code = "12345"
        address_postal_area = "Sevilla"

        query = """
          mutation{{
        	create_address(input:{{
              organization: "{organization_id}",
              name: "{address_name}",
              phone: "{address_phone}",
              street: "{address_street}",
              postal_code: "{address_postal_code}",
              postal_area: "{address_postal_area}"
            }}){{
              errors{{
                field
                messages
              }}
              address{{
                id
                name
                phone
                street
                postal_code
                postal_area
              }}
            }}
          }}
        """.format(organization_id=organization_id, address_name=address_name,
                    address_website=address_website, address_phone=address_phone,
                    address_street=address_street,
                    address_postal_code=address_postal_code,
                    address_postal_area=address_postal_area)

        expected = OrderedDict([('create_address',
                      OrderedDict([('errors', None),
                                   ('address',
                                    OrderedDict([('id', None),
                                                 ('name', address_name),
                                                 ('phone', address_phone),
                                                 ('street', address_street),
                                                 ('postal_code', address_postal_code),
                                                 ('postal_area', address_postal_area),
                                                 ]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        address_id_str = result.data['create_address']['address']['id']
        expected['create_address']['address']['id'] = address_id_str

        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        ## read ##
        query = """
        {{
          getOrganizationById(id: "{organization_id}"){{
            id
            addresses{{
              id
              name
              phone
              street
              postal_code
              postal_area
            }}
          }}
        }}
        """.format(organization_id=organization_id)

        expected = OrderedDict([('getOrganizationById',
                      OrderedDict([('id', organization_id),
                                   ('addresses',
                                    [OrderedDict([('id', address_id_str),
                                                  ('name', address_name),
                                                  ('phone', address_phone),
                                                  ('street', address_street),
                                                  ('postal_code', address_postal_code),
                                                  ('postal_area', address_postal_area)
                                                  ])])]))])


        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        ## update ##
        new_website = "www.emergyadigital.com"
        query = """
          mutation{{
        	update_address(input:{{
              id: "{address_id}",
              organization: "{organization_id}",
              name: "{address_name}",
              phone: "{address_phone}",
              street: "{address_street}",
              postal_code: "{address_postal_code}",
              postal_area: "{address_postal_area}"
            }}){{
              errors{{
                field
                messages
              }}
              address{{
                id
                name
                phone
                street
                postal_code
                postal_area
              }}
            }}
          }}
        """.format(address_id=address_id_str,
                    organization_id=organization_id, address_name=address_name,
                    address_phone=address_phone, address_street=address_street,
                    address_postal_code=address_postal_code,
                    address_postal_area=address_postal_area)

        expected = OrderedDict([('update_address',
                      OrderedDict([('errors', None),
                                   ('address',
                                    OrderedDict([('id', address_id_str),
                                                 ('name', address_name),
                                                 ('phone', address_phone),
                                                 ('street', address_street),
                                                 ('postal_code', address_postal_code),
                                                 ('postal_area', address_postal_area)]))]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        ## delete ##
        query = """
        mutation{{
          delete_address(input: {{
            id: "{address_id}"
          }}){{
            errors{{
              field
              messages
            }}
            success
          }}
        }}
        """.format(address_id=address_id_str)

        expected = OrderedDict([('delete_address',
                      OrderedDict([('errors', None),
                                   ('success', True)
                                   ]))])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )
class CommentsTest(Neo4jGraphQLTest):
    def test_comments_mutations(self):
        ### Comments tests ###
        organization_id = relay.Node.to_global_id('Organization',
                                            str(self.organization1.handle_id))

        ## create ##
        query = """
        mutation{{
          create_comment(
            input:{{
              object_id: "{organization_id}",
              comment: "This comment was added using the graphql api"
            }}
          ){{
            comment{{
              object_id
              comment
              is_public
            }}
          }}
        }}
        """.format(organization_id=organization_id)

        expected =  OrderedDict([('create_comment',
              OrderedDict([('comment',
                            OrderedDict([('object_id', organization_id),
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
          getOrganizationById(id: "{organization_id}"){{
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
              id: "{comment_id}",
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
            id: "{comment_id}"
          }}){{
            success
            id
          }}
        }}
        """.format(comment_id=comment_id)

        expected = OrderedDict([
            ('delete_comment',
                OrderedDict([('success', True), ('id', comment_id)])
            )
        ])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, pformat(result.data, indent=1)

class ValidationTest(Neo4jGraphQLTest):
    def test_node_validation(self):
        # add an abuse contact first
        organization_id = relay.Node.to_global_id('Organization',
                                            str(self.organization1.handle_id))
        organization2_id = relay.Node.to_global_id('Organization',
                                            str(self.organization2.handle_id))
        contact_1 = relay.Node.to_global_id('Contact',
                                            str(self.contact1.handle_id))

        query = '''
        mutation{{
          update_organization(input: {{
            id: "{organization_id}"
            name: "Organization 1"
          }}){{
            errors{{
              field
              messages
            }}
            organization{{
              id
              name
              incoming{{
                name
                relation{{
                  nidata{{
                    name
                    value
                  }}
                  start{{
                    id
                    node_name
                  }}
                }}
              }}
            }}
          }}
        }}
        '''.format(organization_id=organization_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert not result.data['update_organization']['errors'], \
            pformat(result.data['update_organization']['errors'], indent=1)

        # add a non valid contact (an organization)
        query = '''
        mutation{{
          update_organization(input: {{
            id: "{organization_id}"
            name: "Organization 1"
            relationship_parent_of: "{organization_2}"
          }}){{
            errors{{
              field
              messages
            }}
            organization{{
              id
              name
              incoming{{
                name
                relation{{
                  nidata{{
                    name
                    value
                  }}
                  start{{
                    id
                    node_name
                  }}
                }}
              }}
            }}
          }}
        }}
        '''.format(organization_id=organization_id, organization_2=contact_1)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data['update_organization']['errors'], \
            print('{}\n{}'.format(pformat(result.data, indent=1), pformat(result.errors, indent=1)))
