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

        # get the two contacts
        query= """
        {
          contacts(orderBy: handle_id_ASC, first: 2){
            edges{
              node{
                handle_id
                first_name
                last_name
                contact_type
              }
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        contact_1_id = result.data['contacts']['edges'][0]['node']['handle_id']
        contact_1_id = int(contact_1_id)
        contact_1_fname = result.data['contacts']['edges'][0]['node']['first_name']
        contact_1_lname = result.data['contacts']['edges'][0]['node']['last_name']
        contact_2_id = result.data['contacts']['edges'][1]['node']['handle_id']
        contact_2_id = int(contact_2_id)
        contact_2_fname = result.data['contacts']['edges'][1]['node']['first_name']
        contact_2_lname = result.data['contacts']['edges'][1]['node']['last_name']

        assert contact_1_id != contact_2_id, 'The contact ids are equal'

        # create a phone for the first contact
        phone_number = '453-896-3068'
        query = """
        mutation{{
          create_phone(input:{{
            contact: {contact_1_id},
            name: "{phone_number}"
            type: "{phone_type}",
          }}){{
            errors{{
              field
              messages
            }}
            phone{{
              handle_id
              name
              type
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id, phone_number=phone_number,
                    phone_type=phone_type)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert not result.data['create_phone']['errors'], \
            pformat(result.data['create_phone']['errors'], indent=1)

        phone_id = result.data['create_phone']['phone']['handle_id']

        # create an email for the first contact
        email_dir = "cnewby1@joomla.org"
        query = """
        mutation{{
          create_email(input:{{
            contact: {contact_1_id},
            name: "{email_dir}"
            type: "{email_type}",
          }}){{
            errors{{
              field
              messages
            }}
            email{{
              handle_id
              name
              type
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id, email_dir=email_dir,
                    email_type=email_type)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert not result.data['create_email']['errors'], \
            pformat(result.data['create_email']['errors'], indent=1)

        email_id = result.data['create_email']['email']['handle_id']

        # check the contact has the right phone and email set
        query = """
        {{
          getContactById(handle_id: {contact_1_id}){{
            handle_id
            name
            phones{{
              handle_id
            }}
            emails{{
              handle_id
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        tphone_id = result.data['getContactById']['phones'][0]['handle_id']
        temail_id = result.data['getContactById']['emails'][0]['handle_id']

        assert int(phone_id) == int(tphone_id), \
            "Phone id don't match: {} != {}".format(phone_id, tphone_id)

        assert int(email_id) == int(temail_id), \
            "Email id don't match: {} != {}".format(email_id, temail_id)

        # associate first contact to group
        query = """
        mutation{{
          update_contact(input:{{
            handle_id: {contact_1_id},
            first_name: "{contact_1_fname}",
            last_name: "{contact_1_lname}",
            contact_type: "{contact_1_ctype}",
            relationship_member_of: {group_handle_id}
          }}){{
            errors{{
              field
              messages
            }}
            contact{{
              handle_id
              member_of_groups{{
                handle_id
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
            result.data['update_contact']['contact']['member_of_groups'][0]['handle_id']
        assert int(t_group_handle_id) == int(group_handle_id)

        # get the first organization
        query = """
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

        # create address for organization
        website_str = "www.emergya.com"
        street_str = "Calle Luis de Morales, 32, 5º, Puerta 5"
        postal_c_str = "41018"
        postal_a_str = "Seville"
        query = """
        mutation{{
          create_address(input:{{
            organization: {organization_id},
            name: "New address",
            website: "{website_str}",
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
              handle_id
              name
              website
              phone
              street
              postal_code
              postal_area
            }}
          }}
        }}
        """.format(organization_id=organization_id,
            website_str=website_str, phone_number=phone_number,
            street_str=street_str, postal_c_str=postal_c_str,
            postal_a_str=postal_a_str)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        assert not result.data['create_address']['errors'], \
            pformat(result.data['create_address']['errors'], indent=1)

        address_id = result.data['create_address']['address']['handle_id']

        # check the address has been added
        query = """
        {{
          getOrganizationById(handle_id: {organization_id}){{
            handle_id
            name
            addresses{{
              handle_id
              name
              website
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

        taddress_id = result.data['getOrganizationById']['addresses'][0]['handle_id']
        taddress_name = result.data['getOrganizationById']['addresses'][0]['name']
        taddress_website = result.data['getOrganizationById']['addresses'][0]['website']
        taddress_phone = result.data['getOrganizationById']['addresses'][0]['phone']
        taddress_street = result.data['getOrganizationById']['addresses'][0]['street']
        taddress_postal_code = result.data['getOrganizationById']['addresses'][0]['postal_code']
        taddress_postal_area = result.data['getOrganizationById']['addresses'][0]['postal_area']

        assert int(address_id) == int(taddress_id), \
            "Address id don't match: {} != {}".format(address_id, taddress_id)
        assert "New address" == taddress_name, \
            "Address name don't match: {}".format(taddress_name)
        assert website_str == taddress_website, \
            "Address website don't match: {} != {}".format(website_str, taddress_website)
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
          getGroupContactRelations(group_id: {group_handle_id}, contact_id: {contact_1_id}){{
            relation_id
            type
            start{{
              handle_id
            }}
            end{{
              handle_id
            }}
          }}
        }}
        """.format(group_handle_id=group_handle_id, contact_1_id=contact_1_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        start_id = result.data['getGroupContactRelations'][0]['start']['handle_id']
        end_id = result.data['getGroupContactRelations'][0]['end']['handle_id']
        relation_id = result.data['getGroupContactRelations'][0]['relation_id']

        relation_dict = result.data['getGroupContactRelations'][0]

        assert int(start_id) == int(contact_1_id), \
            "Contact id don't match: {} != {}".format(start_id, contact_1_id)

        assert int(end_id) == int(group_handle_id), \
            "Group id don't match: {} != {}".format(end_id, group_handle_id)

        assert relation_id, "Relation id is null"

        # proof that relation exists
        query = """
        {{
          getRelationById(relation_id: {relation_id}){{
            relation_id
            type
            start{{
              handle_id
            }}
            end{{
              handle_id
            }}
          }}
        }}
        """.format(relation_id=relation_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        trelation_dict = result.data['getRelationById']
        assert relation_dict == trelation_dict, \
            "Relations don't match: \n{}\n !=\n {}\n".format(
                pformat(relation_dict, indent=1), pformat(trelation_dict, indent=1))

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
          getContactById(handle_id: {contact_1_id}){{
            handle_id
            member_of_groups{{
              handle_id
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
          getContactEmailRelations(contact_id: {contact_1_id}, email_id: {email_id}){{
            relation_id
            type
            start{{
              handle_id
            }}
            end{{
              handle_id
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id, email_id=email_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        start_id = result.data['getContactEmailRelations'][0]['start']['handle_id']
        end_id = result.data['getContactEmailRelations'][0]['end']['handle_id']
        relation_id = result.data['getContactEmailRelations'][0]['relation_id']

        relation_dict = result.data['getContactEmailRelations'][0]

        assert int(start_id) == int(contact_1_id), \
            "Contact id don't match: {} != {}".format(start_id, contact_1_id)

        assert int(end_id) == int(email_id), \
            "Email id don't match: {} != {}".format(end_id, email_id)

        # proof that relation exists
        query = """
        {{
          getRelationById(relation_id: {relation_id}){{
            relation_id
            type
            start{{
              handle_id
            }}
            end{{
              handle_id
            }}
          }}
        }}
        """.format(relation_id=relation_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        trelation_dict = result.data['getRelationById']
        assert relation_dict == trelation_dict, \
            "Relations don't match: \n{}\n !=\n {}\n".format(
                pformat(relation_dict, indent=1), pformat(trelation_dict, indent=1))

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
          getContactById(handle_id: {contact_1_id}){{
            handle_id
            emails{{
              handle_id
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
          getContactPhoneRelations(contact_id: {contact_1_id}, phone_id: {phone_id}){{
            relation_id
            type
            start{{
              handle_id
            }}
            end{{
              handle_id
            }}
          }}
        }}
        """.format(contact_1_id=contact_1_id, phone_id=phone_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        start_id = result.data['getContactPhoneRelations'][0]['start']['handle_id']
        end_id = result.data['getContactPhoneRelations'][0]['end']['handle_id']
        relation_id = result.data['getContactPhoneRelations'][0]['relation_id']

        relation_dict = result.data['getContactPhoneRelations'][0]

        assert int(start_id) == int(contact_1_id), \
            "Contact id don't match: {} != {}".format(start_id, contact_1_id)

        assert int(end_id) == int(phone_id), \
            "Phone id don't match: {} != {}".format(end_id, phone_id)

        # proof that relation exists
        query = """
        {{
          getRelationById(relation_id: {relation_id}){{
            relation_id
            type
            start{{
              handle_id
            }}
            end{{
              handle_id
            }}
          }}
        }}
        """.format(relation_id=relation_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        trelation_dict = result.data['getRelationById']
        assert relation_dict == trelation_dict, \
            "Relations don't match: \n{}\n !=\n {}\n".format(
                pformat(relation_dict, indent=1), pformat(trelation_dict, indent=1))

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
          getContactById(handle_id: {contact_1_id}){{
            handle_id
            phones{{
              handle_id
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
          getOrganizationAddressRelations(organization_id: {organization_id}, address_id: {address_id}){{
            relation_id
            type
            start{{
              handle_id
            }}
            end{{
              handle_id
            }}
          }}
        }}
        """.format(organization_id=organization_id, address_id=address_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        start_id = result.data['getOrganizationAddressRelations'][0]['start']['handle_id']
        end_id = result.data['getOrganizationAddressRelations'][0]['end']['handle_id']
        relation_id = result.data['getOrganizationAddressRelations'][0]['relation_id']

        relation_dict = result.data['getOrganizationAddressRelations'][0]

        assert int(start_id) == int(organization_id), \
            "Contact id don't match: {} != {}".format(start_id, organization_id)

        assert int(end_id) == int(address_id), \
            "Phone id don't match: {} != {}".format(end_id, address_id)

        # proof that relation exists
        query = """
        {{
          getRelationById(relation_id: {relation_id}){{
            relation_id
            type
            start{{
              handle_id
            }}
            end{{
              handle_id
            }}
          }}
        }}
        """.format(relation_id=relation_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        trelation_dict = result.data['getRelationById']
        assert relation_dict == trelation_dict, \
            "Relations don't match: \n{}\n !=\n {}\n".format(
                pformat(relation_dict, indent=1), pformat(trelation_dict, indent=1))

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
          getOrganizationById(handle_id: {organization_id}){{
            handle_id
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
