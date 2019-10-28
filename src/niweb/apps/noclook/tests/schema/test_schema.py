# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, Dropdown, Choice, Role, Group, GroupContextAuthzAction, NodeHandleContext
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
        street_str = "Calle Luis de Morales, 32, 5º, Puerta 5"
        postal_c_str = "41018"
        postal_a_str = "Seville"
        query = """
        mutation{{
          create_address(input:{{
            organization: {organization_id},
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
              handle_id
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
        taddress_phone = result.data['getOrganizationById']['addresses'][0]['phone']
        taddress_street = result.data['getOrganizationById']['addresses'][0]['street']
        taddress_postal_code = result.data['getOrganizationById']['addresses'][0]['postal_code']
        taddress_postal_area = result.data['getOrganizationById']['addresses'][0]['postal_area']

        assert int(address_id) == int(taddress_id), \
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
              handle_id
              name
            }
          }
        }
        """
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        organization3_id = result.data['create_organization']['organization']['handle_id']

        # create a new contact for this organization
        query = """
        mutation{{
          create_contact(input:{{
            first_name: "Jasmine"
            last_name: "Svensson"
            contact_type: "person"
            relationship_works_for: {organization_id}
          }}){{
            errors{{
              field
              messages
            }}
            contact{{
              handle_id
              name
            }}
          }}
        }}
        """.format(organization_id=organization3_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        contact3_id = result.data['create_contact']['contact']['handle_id']

        # add email and get id
        query = """
        mutation{{
          create_email(input:{{
            name: "jsvensson@emergya.com"
            type: "work"
            contact: {contact_id}
          }}){{
            errors{{
              field
              messages
            }}
            email{{
              handle_id
              name
            }}
          }}
        }}
        """.format(contact_id=contact3_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        email3_id = result.data['create_email']['email']['handle_id']

        # add phone and get id
        query = """
        mutation{{
          create_phone(input:{{
            name: "+34606000606"
            type: "work"
            contact: {contact_id}
          }}){{
            errors{{
              field
              messages
            }}
            phone{{
              handle_id
              name
            }}
          }}
        }}
        """.format(contact_id=contact3_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        phone3_id = result.data['create_phone']['phone']['handle_id']

        # delete contact
        query = """
        mutation{{
          delete_contact(input:{{ handle_id: {contact_id} }}){{
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
          organizations(filter:{{ AND:[{{ handle_id: {organization_id} }}] }}){{
            edges{{
              node{{
                handle_id
                name
              }}
            }}
          }}
        }}
        """.format(organization_id=organization3_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        edges = result.data['organizations']['edges']
        assert edges, \
            "Organization query is empty:\n {}".format(pformat(edges, indent=1))
        test_org_id = result.data['organizations']['edges'][0]['node']['handle_id']
        assert int(test_org_id) == int(organization3_id), \
            print("Organization doesn't exists")

        # check email and phone are deleted
        query = """
        {{
          emails(filter:{{ AND:[{{ handle_id: {email_id} }}] }}){{
            edges{{
              node{{
                handle_id
                name
              }}
            }}
          }}
        }}
        """.format(email_id=email3_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        edges = result.data['emails']['edges']
        assert not edges, pformat(edges, indent=1)

        query = """
        {{
          phones(filter:{{ AND:[{{ handle_id: {phone_id} }}] }}){{
            edges{{
              node{{
                handle_id
                name
              }}
            }}
          }}
        }}
        """.format(phone_id=phone3_id)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        edges = result.data['phones']['edges']
        assert not edges, pformat(edges, indent=1)

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
              organization: {organization_id},
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
                handle_id
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
        address_id_str = result.data['create_address']['address']['handle_id']

        # delete organization
        query = """
        mutation{{
          delete_organization(input:{{ handle_id: {organization_id} }}){{
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
          addresss(filter:{{ AND:[{{ handle_id: {address_id_str} }}] }}){{
            edges{{
              node{{
                handle_id
                name
              }}
            }}
          }}
        }}
        """.format(address_id_str=address_id_str)
        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        edges = result.data['addresss']['edges']
        assert not edges, pformat(edges, indent=1)


    def test_multiple_mutation(self):
        # create two new contacts to delete
        self.contact5 = self.create_node('contact5', 'contact', meta='Relation')
        self.contact6 = self.create_node('contact6', 'contact', meta='Relation')

        NodeHandleContext(nodehandle=self.contact5, context=self.community_ctxt).save()
        NodeHandleContext(nodehandle=self.contact6, context=self.community_ctxt).save()

        # add some data
        contact5_data = {
            'first_name': 'Fritz',
            'last_name': 'Lang',
            'name': 'Fritz Lang',
            'contact_type': 'person',
        }

        for key, value in contact5_data.items():
            self.contact5.get_node().add_property(key, value)

        contact6_data = {
            'first_name': 'John',
            'last_name': 'Smith',
            'name': 'John Smith',
            'contact_type': 'person',
        }

        for key, value in contact6_data.items():
            self.contact6.get_node().add_property(key, value)

        # get two existent contacts
        query = '''
        query {
          contacts(first: 2, orderBy: handle_id_ASC) {
            edges {
              node {
                handle_id
                first_name
                last_name
                member_of_groups {
                  name
                }
                roles{
                  relation_id
                  name
                }
              }
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        c1_id = result.data['contacts']['edges'][0]['node']['handle_id']
        c1_fname = result.data['contacts']['edges'][0]['node']['first_name']
        c1_lname = result.data['contacts']['edges'][0]['node']['last_name']
        c2_id = result.data['contacts']['edges'][1]['node']['handle_id']
        c2_fname = result.data['contacts']['edges'][1]['node']['first_name']
        c2_lname = result.data['contacts']['edges'][1]['node']['last_name']
        detach_r1_id = result.data['contacts']['edges'][0]['node']['roles'][0]['relation_id']
        detach_r2_id = result.data['contacts']['edges'][1]['node']['roles'][0]['relation_id']

        # get two roles
        query = """
        {
          roles(last:2){
            edges{
              node{
                handle_id
                name
                slug
                description
              }
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        role1_id = result.data['roles']['edges'][0]['node']['handle_id']
        role2_id = result.data['roles']['edges'][1]['node']['handle_id']

        # create new group
        new_group_name = "Workshop group"
        query = '''
        mutation {{
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
        group_id = result.data['create_group']['group']['handle_id']

        # create new organization
        query = """
        mutation{
          create_organization(
            input: {
              name: "Didactum Workshops",
              description: "This is the description of the new organization",
            }
          ){
            organization{
              handle_id
              name
              description
            }
          }
        }
        """

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)
        organization_id = result.data['create_organization']['organization']['handle_id']

        title_1 = "Mr/Ms"
        title_2 = "Dr"
        note_news = "New employees"
        note_updated = "Promoted employees"
        c3_fname = "James"
        c3_lname = "Smith"
        c4_fname = "Carol"
        c4_lname = "Svensson"
        delete_c1_id = self.contact5.handle_id
        delete_c2_id = self.contact6.handle_id

        query = '''
        mutation{{
          multiple_contact(
            input:{{
              create_inputs:[
                {{
                  title: "{title_1}"
                  first_name: "{c3_fname}"
                  last_name: "{c3_lname}"
                  contact_type: "person"
                  relationship_works_for: {organization_id}
                  role: {role1_id}
                  relationship_member_of: {group_id}
                  notes: "{note_news}"
                }}
                {{
                  title: "{title_1}"
                  first_name: "{c4_fname}"
                  last_name: "{c4_lname}"
                  contact_type: "person"
                  relationship_works_for: {organization_id}
                  role: {role1_id}
                  relationship_member_of: {group_id}
                  notes: "{note_news}"
                }}
              ]
              update_inputs:[
                {{
                  handle_id: {c1_id}
                  title: "{title_2}"
                  first_name: "{c1_fname}"
                  last_name: "{c1_lname}"
                  contact_type: "person"
                  relationship_works_for: {organization_id}
                  role: {role2_id}
                  relationship_member_of: {group_id}
                  notes: "{note_updated}"
                }}
                {{
                  handle_id: {c2_id}
                  title: "{title_2}"
                  first_name: "{c2_fname}"
                  last_name: "{c2_lname}"
                  contact_type: "person"
                  relationship_works_for: {organization_id}
                  role: {role2_id}
                  relationship_member_of: {group_id}
                  notes: "{note_updated}"
                }}
              ]
              delete_inputs:[
              	{{
                  handle_id: {delete_c1_id}
                }}
                {{
                  handle_id: {delete_c2_id}
                }}
            	]
              detach_inputs:[
                {{
                  relation_id: {detach_r1_id}
                }}
                {{
                  relation_id: {detach_r2_id}
                }}
              ]
            }}
          ){{
            created{{
              errors{{
                field
                messages
              }}
              contact{{
                handle_id
                title
                first_name
                last_name
                contact_type
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
            updated{{
              errors{{
                field
                messages
              }}
              contact{{
                handle_id
                title
                first_name
                last_name
                contact_type
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
            deleted{{
              errors{{
                field
                messages
              }}
              success
            }}
            detached{{
              success
              relation_id
            }}
          }}
        }}
        '''.format(organization_id=organization_id, group_id=group_id,
                    role1_id=role1_id, role2_id=role2_id, title_1=title_1,
                    title_2=title_2, note_news=note_news, note_updated=note_updated,
                    c1_id=c1_id, c1_fname=c1_fname, c1_lname=c1_lname,
                    c2_id=c2_id, c2_fname=c2_fname, c2_lname=c2_lname,
                    c3_fname=c3_fname, c3_lname=c3_lname, c4_fname=c4_fname,
                    c4_lname=c4_lname, delete_c1_id=delete_c1_id,
                    delete_c2_id=delete_c2_id, detach_r1_id=detach_r1_id,
                    detach_r2_id=detach_r2_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors in each mutation group
        created_data = result.data['multiple_contact']['created']
        updated_data = result.data['multiple_contact']['updated']
        deleted_data = result.data['multiple_contact']['deleted']
        detached_data = result.data['multiple_contact']['detached']

        for c_data in created_data:
            assert not c_data['errors']

        for u_data in updated_data:
            assert not u_data['errors']

        for d_data in deleted_data:
            assert not d_data['errors']
            assert d_data['success']

        for de_data in detached_data:
            assert de_data['success']

        # check created data
        query = '''
        query {
          contacts(first: 2, orderBy: handle_id_DESC) {
            edges {
              node {
                first_name
                last_name
                member_of_groups {
                  handle_id
                  name
                }
                roles{
                  relation_id
                  name
                  end{
                    handle_id
                    node_name
                  }
                }
              }
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        assert result.data['contacts']['edges'][1]['node']['first_name'] == c3_fname
        assert result.data['contacts']['edges'][1]['node']['last_name'] == c3_lname

        assert result.data['contacts']['edges'][0]['node']['first_name'] == c4_fname
        assert result.data['contacts']['edges'][0]['node']['last_name'] == c4_lname

        assert result.data['contacts']['edges'][0]['node']['roles'][0]['end']['handle_id'] == organization_id
        assert result.data['contacts']['edges'][1]['node']['roles'][0]['end']['handle_id'] == organization_id

        assert result.data['contacts']['edges'][0]['node']['member_of_groups'][0]['handle_id'] == group_id
        assert result.data['contacts']['edges'][1]['node']['member_of_groups'][0]['handle_id'] == group_id

        # check edited data
        query = '''
        query {
          contacts(first: 2, orderBy: handle_id_ASC) {
            edges {
              node {
                first_name
                last_name
                member_of_groups {
                  handle_id
                  name
                }
                roles{
                  relation_id
                  name
                  end{
                    handle_id
                    node_name
                  }
                }
              }
            }
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        assert result.data['contacts']['edges'][0]['node']['first_name'] == c1_fname
        assert result.data['contacts']['edges'][0]['node']['last_name'] == c1_lname

        assert result.data['contacts']['edges'][1]['node']['first_name'] == c2_fname
        assert result.data['contacts']['edges'][1]['node']['last_name'] == c2_lname

        assert result.data['contacts']['edges'][0]['node']['roles'][0]['end']['handle_id'] == organization_id
        assert result.data['contacts']['edges'][1]['node']['roles'][0]['end']['handle_id'] == organization_id

        assert \
            result.data['contacts']['edges'][0]['node']['member_of_groups'][-1]['handle_id'] == group_id, \
            pformat(result.data, indent=1)
        assert \
            result.data['contacts']['edges'][1]['node']['member_of_groups'][-1]['handle_id'] == group_id, \
            pformat(result.data, indent=1)

        # check that the previous contacts are detached of their previous org
        assert len(result.data['contacts']['edges'][0]['node']['roles']) == 1
        assert len(result.data['contacts']['edges'][1]['node']['roles']) == 1

        # check deleted data
        query_getcontact = '''
        {{
          getContactById(handle_id: {contact_id}){{
            handle_id
            first_name
            last_name
          }}
        }}
        '''

        query = query_getcontact.format(contact_id=delete_c1_id)
        result = schema.execute(query, context=self.context)
        assert result.errors, pformat(result.errors, indent=1)

        query = query_getcontact.format(contact_id=delete_c2_id)
        result = schema.execute(query, context=self.context)
        assert result.errors, pformat(result.errors, indent=1)
