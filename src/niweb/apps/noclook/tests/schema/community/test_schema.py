# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, Dropdown, Choice, Role, Group, \
    GroupContextAuthzAction, NodeHandleContext, DEFAULT_ROLEGROUP_NAME
from collections import OrderedDict
from django.utils.dateparse import parse_datetime
from graphene import relay
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLCommunityTest

from datetime import datetime

class SimpleListTest(Neo4jGraphQLCommunityTest):
    def test_simple_list(self):
        # query all available types
        test_types = {
            'organization': [self.organization1, self.organization2],
            'contact': [self.contact1, self.contact2],
            'group': [self.group1, self.group2],
        }

        for name, nodes in test_types.items():
            query = '''
            {{
              all_{}s {{
                handle_id
                node_name
              }}
            }}
            '''.format(name)

            node_list = []

            for node in nodes:
                node_dict = OrderedDict([
                    ('handle_id', str(node.handle_id)),
                    ('node_name', node.node_name)
                ])
                node_list.append(node_dict)

            expected = OrderedDict([
                ('all_{}s'.format(name), node_list)
            ])

            result = schema.execute(query, context=self.context)
            assert not result.errors, pformat(result.errors, indent=1)

            assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

class ConnectionsTest(Neo4jGraphQLCommunityTest):
    def test_connections(self):
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
              member_of_groups: { name: "Group2" },
              roles: { name: "Role2"}
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
              member_of_groups_in: [{ name: "Group1" }, { name: "gRoup2" }],
              roles_in: [{ name: "ROLE1" }, { name: "role2" }]
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
              member_of_groups: { name: "Group2" },
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
        test_org_type = 'university_college'
        for pair in result.data['getChoicesForDropdown']:
            if pair['value'] == test_org_type:
                found = True
                break

        assert found, pformat(result.data, indent=1)

        query = '''
        {
        	organizations(filter:{
            AND: [
              { type: "university_college" }
            ]
          }){
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


class DropdownTest(Neo4jGraphQLCommunityTest):
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


class RelationResolversTest(Neo4jGraphQLCommunityTest):
    def test_relation_resolvers(self):
        ## get aux entities types
        # get phone types
        query = """
        {
          getChoicesForDropdown(name: "contact_type"){
            value
          }
        }
        """
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        contact_type = result.data['getChoicesForDropdown'][-1]['value']

        # get phone types
        query = """
        {
          getChoicesForDropdown(name: "phone_type"){
            value
          }
        }
        """
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        phone_type = result.data['getChoicesForDropdown'][-1]['value']

        # get email types
        query = """
        {
          getChoicesForDropdown(name: "email_type"){
            value
          }
        }
        """
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        email_type = result.data['getChoicesForDropdown'][-1]['value']


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

        # get the two contacts
        query= """
        {
          contacts(orderBy: handle_id_ASC, first: 2){
            edges{
              node{
                id
                first_name
                last_name
                contact_type{
                  name
                  value
                }
              }
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        contact_1_id = result.data['contacts']['edges'][0]['node']['id']
        contact_1_fname = result.data['contacts']['edges'][0]['node']['first_name']
        contact_1_lname = result.data['contacts']['edges'][0]['node']['last_name']
        contact_2_id = result.data['contacts']['edges'][1]['node']['id']
        contact_2_fname = result.data['contacts']['edges'][1]['node']['first_name']
        contact_2_lname = result.data['contacts']['edges'][1]['node']['last_name']

        assert contact_1_id != contact_2_id, 'The contact ids are equal'

        # create a phone for the first contact
        phone_number = '453-896-3068'
        query = """
        mutation{{
          create_phone(input:{{
            contact: "{contact_1_id}",
            name: "{phone_number}"
            type: "{phone_type}",
          }}){{
            errors{{
              field
              messages
            }}
            phone{{
              id
              name
              type{{
                name
                value
              }}
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id, phone_number=phone_number,
                    phone_type=phone_type)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert not result.data['create_phone']['errors'], \
            pformat(result.data['create_phone']['errors'], indent=1)

        phone_id = result.data['create_phone']['phone']['id']

        # create an email for the first contact
        email_dir = "cnewby1@joomla.org"
        query = """
        mutation{{
          create_email(input:{{
            contact: "{contact_1_id}",
            name: "{email_dir}"
            type: "{email_type}",
          }}){{
            errors{{
              field
              messages
            }}
            email{{
              id
              name
              type{{
                name
                value
              }}
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id, email_dir=email_dir,
                    email_type=email_type)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert not result.data['create_email']['errors'], \
            pformat(result.data['create_email']['errors'], indent=1)

        email_id = result.data['create_email']['email']['id']

        # check the contact has the right phone and email set
        query = """
        {{
          getContactById(id: "{contact_1_id}"){{
            id
            name
            phones{{
              id
            }}
            emails{{
              id
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        tphone_id = result.data['getContactById']['phones'][0]['id']
        temail_id = result.data['getContactById']['emails'][0]['id']

        assert phone_id == tphone_id, \
            "Phone id don't match: {} != {}".format(phone_id, tphone_id)

        assert email_id == temail_id, \
            "Email id don't match: {} != {}".format(email_id, temail_id)

        # associate first contact to group
        query = """
        mutation{{
          update_contact(input:{{
            id: "{contact_1_id}",
            first_name: "{contact_1_fname}",
            last_name: "{contact_1_lname}",
            contact_type: "{contact_1_ctype}",
            relationship_member_of: "{group_handle_id}"
          }}){{
            errors{{
              field
              messages
            }}
            contact{{
              handle_id
              member_of_groups{{
                id
              }}
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id, contact_1_fname=contact_1_fname,
                    contact_1_lname=contact_1_lname,
                    contact_1_ctype=contact_type,
                    group_handle_id=group_handle_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert not result.data['update_contact']['errors'], \
            pformat(result.data['update_contact']['errors'], indent=1)

        t_group_handle_id = \
            result.data['update_contact']['contact']['member_of_groups'][0]['id']
        assert t_group_handle_id == group_handle_id

        # get the first organization
        query = """
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

        # create address for organization
        street_str = "Calle Luis de Morales, 32, 5º, Puerta 5"
        postal_c_str = "41018"
        postal_a_str = "Seville"
        query = """
        mutation{{
          create_address(input:{{
            organization: "{organization_id}",
            name: "New address",
            phone: "{phone_number}",
            street: "{street_str}",
            postal_code: "{postal_c_str}",
            postal_area: "{postal_a_str}",
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
        """.format(organization_id=organization_id,
            phone_number=phone_number, street_str=street_str,
            postal_c_str=postal_c_str, postal_a_str=postal_a_str)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert not result.data['create_address']['errors'], \
            pformat(result.data['create_address']['errors'], indent=1)

        address_id = result.data['create_address']['address']['id']

        # check the address has been added
        query = """
        {{
          getOrganizationById(id: "{organization_id}"){{
            id
            name
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

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        taddress_id = result.data['getOrganizationById']['addresses'][0]['id']
        taddress_name = result.data['getOrganizationById']['addresses'][0]['name']
        taddress_phone = result.data['getOrganizationById']['addresses'][0]['phone']
        taddress_street = result.data['getOrganizationById']['addresses'][0]['street']
        taddress_postal_code = result.data['getOrganizationById']['addresses'][0]['postal_code']
        taddress_postal_area = result.data['getOrganizationById']['addresses'][0]['postal_area']

        assert address_id == taddress_id, \
            "Address id don't match: {} != {}".format(address_id, taddress_id)
        assert "New address" == taddress_name, \
            "Address name don't match: {}".format(taddress_name)
        assert phone_number == taddress_phone, \
            "Address phone don't match: {} != {}".format(phone_number, taddress_phone)
        assert street_str == taddress_street, \
            "Address string don't match: {} != {}".format(phone_number, taddress_street)
        assert postal_c_str == taddress_postal_code, \
            "Address string don't match: {} != {}".format(postal_c_str, taddress_postal_code)
        assert postal_a_str == taddress_postal_area, \
            "Address string don't match: {} != {}".format(postal_a_str, taddress_postal_area)

        # get relation from Group - Contact
        query = """
        {{
          getGroupById(id: "{group_handle_id}"){{
            id
            name
            contacts{{
              id
              name
              relation_id
            }}
          }}
        }}
        """.format(group_handle_id=group_handle_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        relation_id = result.data['getGroupById']['contacts'][0]['relation_id']
        assert relation_id, "Relation id is null"

        # delete relationship
        query = """
        mutation{{
          delete_relationship(input:{{
            relation_id: {relation_id}
          }}){{
            success
          }}
        }}
        """.format(relation_id=relation_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check that it doesn't exist anymore
        query = """
        {{
          getContactById(id: "{contact_1_id}"){{
            id
            member_of_groups{{
              id
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        contact_groups = result.data['getContactById']['member_of_groups']
        assert not contact_groups, "Groups should be empty \n{}".format(
            pformat(contact_groups, indent=1)
        )

        # get relation from Contact - Email
        query = """
        {{
          getContactById(id: "{contact_1_id}"){{
            id
            emails{{
              relation_id
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        relation_id = result.data['getContactById']['emails'][0]['relation_id']
        assert relation_id, "Relation id is null"

        # delete relationship
        query = """
        mutation{{
          delete_relationship(input:{{
            relation_id: {relation_id}
          }}){{
            success
          }}
        }}
        """.format(relation_id=relation_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check that it doesn't exist anymore
        query = """
        {{
          getContactById(id: "{contact_1_id}"){{
            id
            emails{{
              id
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        contact_emails = result.data['getContactById']['emails']
        assert not contact_emails, "Emails should be empty \n{}".format(
            pformat(contact_emails, indent=1)
        )

        # get relation from Contact - Phone
        query = """
        {{
          getContactById(id: "{contact_1_id}"){{
            id
            phones{{
              relation_id
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        relation_id = result.data['getContactById']['phones'][0]['relation_id']
        assert relation_id, "Relation id is null"

        # delete relationship
        query = """
        mutation{{
          delete_relationship(input:{{
            relation_id: {relation_id}
          }}){{
            success
          }}
        }}
        """.format(relation_id=relation_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check that it doesn't exist anymore
        query = """
        {{
          getContactById(id: "{contact_1_id}"){{
            id
            phones{{
              id
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        contact_phones = result.data['getContactById']['phones']
        assert not contact_phones, "Phones should be empty \n{}".format(
            pformat(contact_phones, indent=1)
        )

        # get relation from Organization - Address
        query = """
        {{
          getOrganizationById(id: "{organization_id}"){{
            id
            addresses{{
              relation_id
            }}
          }}
        }}
        """.format(organization_id=organization_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        relation_id = result.data['getOrganizationById']['addresses'][0]['relation_id']
        assert relation_id, "Relation id is null"

        # delete relationship
        query = """
        mutation{{
          delete_relationship(input:{{
            relation_id: {relation_id}
          }}){{
            success
          }}
        }}
        """.format(relation_id=relation_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check that it doesn't exist anymore
        query = """
        {{
          getOrganizationById(id: "{organization_id}"){{
            id
            addresses{{
              handle_id
            }}
          }}
        }}
        """.format(organization_id=organization_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        organization_addresses = result.data['getOrganizationById']['addresses']
        assert not organization_addresses, "Address array should be empty \n{}".format(
            pformat(organization_addresses, indent=1)
        )


class CascadeDeleteTest(Neo4jGraphQLCommunityTest):
    def test_cascade_delete(self):
        ## get aux entities types
        # get contact types
        query = """
        {
          getChoicesForDropdown(name: "organization_types"){
            value
          }
        }
        """
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        organization_type = result.data['getChoicesForDropdown'][-1]['value']

        # get contact types
        query = """
        {
          getChoicesForDropdown(name: "contact_type"){
            value
          }
        }
        """
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        contact_type = result.data['getChoicesForDropdown'][-1]['value']

        # get phone types
        query = """
        {
          getChoicesForDropdown(name: "phone_type"){
            value
          }
        }
        """
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        phone_type = result.data['getChoicesForDropdown'][-1]['value']

        # get email types
        query = """
        {
          getChoicesForDropdown(name: "email_type"){
            value
          }
        }
        """
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        email_type = result.data['getChoicesForDropdown'][-1]['value']

        # create new organization
        query = """
        mutation{
          create_organization(
            input:{
              name: "Emergya"
              description: "A test organization"
            }
          ){
            errors{
              field
              messages
            }
            organization{
              id
              name
            }
          }
        }
        """
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        organization3_id = result.data['create_organization']['organization']['id']

        # create a new contact for this organization
        query = """
        mutation{{
          create_contact(input:{{
            first_name: "Jasmine"
            last_name: "Svensson"
            contact_type: "person"
            relationship_works_for: "{organization_id}"
          }}){{
            errors{{
              field
              messages
            }}
            contact{{
              id
              name
            }}
          }}
        }}
        """.format(organization_id=organization3_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        contact3_id = result.data['create_contact']['contact']['id']

        # add email and get id
        query = """
        mutation{{
          create_email(input:{{
            name: "jsvensson@emergya.com"
            type: "work"
            contact: "{contact_id}"
          }}){{
            errors{{
              field
              messages
            }}
            email{{
              id
              name
            }}
          }}
        }}
        """.format(contact_id=contact3_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        email3_id = result.data['create_email']['email']['id']

        # add phone and get id
        query = """
        mutation{{
          create_phone(input:{{
            name: "+34606000606"
            type: "work"
            contact: "{contact_id}"
          }}){{
            errors{{
              field
              messages
            }}
            phone{{
              id
              name
            }}
          }}
        }}
        """.format(contact_id=contact3_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        phone3_id = result.data['create_phone']['phone']['id']

        # delete contact
        query = """
        mutation{{
          delete_contact(input:{{ id: "{contact_id}" }}){{
            errors{{
              field
              messages
            }}
            success
          }}
        }}
        """.format(contact_id=contact3_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        errors = result.data['delete_contact']['errors']
        success = result.data['delete_contact']['success']
        assert not errors, pformat(errors, indent=1)
        assert success, pformat(success, indent=1)

        # check organization still exists
        query = """
        {{
          getOrganizationById( id: "{organization_id}" ){{
            id
            name
          }}
        }}
        """.format(organization_id=organization3_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        edges = result.data['getOrganizationById']
        assert edges, \
            "Organization query is empty:\n {}".format(pformat(edges, indent=1))
        test_org_id = result.data['getOrganizationById']['id']
        assert test_org_id == organization3_id, \
            print("Organization doesn't exists")

        # check email and phone are deleted
        query = """
        {{
          getEmailById( id: "{email_id}" ){{
            handle_id
            name
          }}
        }}
        """.format(email_id=email3_id)
        result = schema.execute(query, context=self.context)

        expected_error = [()]
        assert result.errors, pformat(result, indent=1)

        query = """
        {{
          getPhoneById( id: "{phone_id}" ){{
            id
            name
          }}
        }}
        """.format(phone_id=phone3_id)
        result = schema.execute(query, context=self.context)
        assert result.errors, pformat(result, indent=1)

        # create address
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
        """.format(organization_id=organization3_id, address_name=address_name,
                    address_phone=address_phone, address_street=address_street,
                    address_postal_code=address_postal_code,
                    address_postal_area=address_postal_area)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        address_id_str = result.data['create_address']['address']['id']

        # delete organization
        query = """
        mutation{{
          delete_organization(input:{{ id: "{organization_id}" }}){{
            errors{{
              field
              messages
            }}
            success
          }}
        }}
        """.format(organization_id=organization3_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        errors = result.data['delete_organization']['errors']
        success = result.data['delete_organization']['success']
        assert not errors, pformat(errors, indent=1)
        assert success, pformat(success, indent=1)

        # check address is deleted
        query = """
        {{
          getAddressById( id: {address_id_str} ){{
            edges{{
              node{{
                id
                name
              }}
            }}
          }}
        }}
        """.format(address_id_str=address_id_str)
        result = schema.execute(query, context=self.context)
        assert result.errors, pformat(result, indent=1)


class RoleGroupTest(Neo4jGraphQLCommunityTest):
    def test_rolegroup(self):
        query = '''
        {
          getAvailableRoleGroups{
            name
          }
        }
        '''

        expected = []

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        found = False

        for rolegroups in result.data['getAvailableRoleGroups']:
            for k, gname in rolegroups.items():
                if gname == DEFAULT_ROLEGROUP_NAME:
                    found = True

        assert found, pformat(result.data, indent=1)

        query = """
        {
          getRolesFromRoleGroup{
            handle_id
            name
            slug
            description
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        no_args_roles = result.data['getRolesFromRoleGroup']

        query = '''
        {{
          getRolesFromRoleGroup(name: "{default_rolegroup}"){{
            handle_id
            name
            slug
            description
          }}
        }}
        '''.format(default_rolegroup=DEFAULT_ROLEGROUP_NAME)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        args_roles = result.data['getRolesFromRoleGroup']

        assert args_roles == no_args_roles, "{}\n!=\n{}".format(
            pformat(no_args_roles, indent=1),
            pformat(args_roles, indent=1)
        )

class CheckExistentOrganizationIdTest(Neo4jGraphQLCommunityTest):
    def test_check_organization_id(self):
        # first try and check one that exists
        nh = self.organization1
        organization1_id = relay.Node.to_global_id(str(nh.node_type),
                                            str(nh.handle_id))
        organization1_orgid = nh.get_node().data.get('organization_id')

        query = '''
        {{
          checkExistentOrganizationId(organization_id: "{organization1_orgid}")
        }}
        '''.format(organization1_orgid=organization1_orgid)

        expected = {'checkExistentOrganizationId': True}

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '\n{} \n != {}'.format(
                                            pformat(result.data, indent=1),
                                            pformat(expected, indent=1)
                                        )

        # then check that it returns false when the id is passed
        query = '''
        {{
          checkExistentOrganizationId(organization_id: "{organization1_orgid}", id: "{organization1_id}")
        }}
        '''.format(organization1_orgid=organization1_orgid, organization1_id=organization1_id)

        expected = {'checkExistentOrganizationId': False}

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '\n{} \n != {}'.format(
                                            pformat(result.data, indent=1),
                                            pformat(expected, indent=1)
                                        )

        # last, check that an organization id that doesn't exists
        organization1_orgid = "ORG3"
        query = '''
        {{
          checkExistentOrganizationId(organization_id: "{organization1_orgid}")
        }}
        '''.format(organization1_orgid=organization1_orgid)

        expected = {'checkExistentOrganizationId': False}

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert result.data == expected, '\n{} \n != {}'.format(
                                            pformat(result.data, indent=1),
                                            pformat(expected, indent=1)
                                        )


class EmptyCommunityDataTest(Neo4jGraphQLCommunityTest):
    def test_contact_empty_first_name(self):
        # remove first_name from contact1
        c1_node = self.contact1.get_node()
        c1_node.remove_property('first_name')

        contact_1_id = relay.Node.to_global_id(str(self.contact1.node_type),
                                            str(self.contact1.handle_id))

        # do a simple contact query and check that there's no errors
        query = """
        {{
          getContactById(id: "{contact_1_id}"){{
            id
            first_name
          }}
        }}
        """.format(contact_1_id=contact_1_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = {
            'getContactById': {
                'id': contact_1_id,
                'first_name': '',
            }
        }

        assert result.data == expected, '{} \n != {}'.format(
                                            pformat(result.data, indent=1),
                                            pformat(expected, indent=1)
                                        )
