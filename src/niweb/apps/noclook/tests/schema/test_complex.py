# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, Dropdown, Choice, Role, Group, \
    GroupContextAuthzAction, NodeHandleContext, DEFAULT_ROLEGROUP_NAME
from collections import OrderedDict
from . import Neo4jGraphQLTest
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLTest

class GroupComplexTest(Neo4jGraphQLTest):
    def test_composite_group(self):
        group_name = "The Pendletones"
        description_group = "In sodales nisl et turpis sollicitudin, nec \
        feugiat erat egestas. Nam pretium felis vel dolor euismod ornare. \
        Praesent consectetur risus sit amet lectus scelerisque, non \
        sollicitudin dolor luctus. Aliquam pretium neque non purus dictum \
        blandit."

        contact_type = "person"
        email_type = "work"
        phone_type = "work"

        c1_first_name = "Brian"
        c1_last_name = "Wilson"
        c1_mail = 'bwilson@pendletones.com'
        c1_phone = '555-123456'

        c2_first_name = "Mike"
        c2_last_name = "Love"
        c2_mail = 'mlove@pendletones.com'
        c2_phone = '555-987654'

        c3_first_name = "Murry"
        c3_last_name = "Wilson"
        c3_mail = 'mwilson@pendletones.com'
        c3_phone = '555-987654'

        # Create query

        query = '''
        mutation{{
          composite_group(input:{{
            create_input:{{
              name: "{group_name}"
              description: "{description_group}"
            }}
            create_subinputs:[
              {{
                first_name: "{c1_first_name}"
                last_name: "{c1_last_name}"
                contact_type: "{contact_type1}"
                email: "{c1_mail}"
                email_type: "{email_type1}"
                phone: "{c1_phone}"
                phone_type: "{phone_type1}"
              }}
              {{
                first_name: "{c2_first_name}"
                last_name: "{c2_last_name}"
                contact_type: "{contact_type2}"
                email: "{c2_mail}"
                email_type: "{email_type2}"
              }}
              {{
                first_name: "{c3_first_name}"
                last_name: "{c3_last_name}"
                contact_type: "{contact_type1}"
                email: "{c3_mail}"
                email_type: "{email_type1}"
                phone: "{c3_phone}"
                phone_type: "{phone_type1}"
              }}
            ]
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              group{{
                handle_id
                name
                description
                contacts{{
                  handle_id
                  first_name
                  last_name
                }}
              }}
            }}
            subcreated{{
              errors{{
                field
                messages
              }}
              contact{{
                handle_id
                first_name
                last_name
                emails{{
                  handle_id
                  name
                }}
                phones{{
                  handle_id
                  name
                }}
                member_of_groups{{
                  name
                }}
              }}
            }}
          }}
        }}
        '''.format(group_name=group_name, description_group=description_group,
                    c1_first_name=c1_first_name, c1_last_name=c1_last_name,
                    contact_type1=contact_type, c1_mail=c1_mail,
                    email_type1=email_type, c1_phone=c1_phone,
                    phone_type1=phone_type, c2_first_name=c2_first_name,
                    c2_last_name=c2_last_name, contact_type2=contact_type,
                    c2_mail=c2_mail, email_type2=email_type,
                    c3_first_name=c3_first_name, c3_last_name=c3_last_name,
                    c3_mail=c3_mail, c3_phone=c3_phone)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_group']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        for subcreated in result.data['composite_group']['subcreated']:
            assert not subcreated['errors']

        # get the ids
        result_data = result.data['composite_group']
        group_handle_id = result_data['created']['group']['handle_id']
        c1_handle_id = result_data['subcreated'][0]['contact']['handle_id']
        c1_email_id = result_data['subcreated'][0]['contact']['emails'][0]['handle_id']
        c1_phone_id = result_data['subcreated'][0]['contact']['phones'][0]['handle_id']
        c2_handle_id = result_data['subcreated'][1]['contact']['handle_id']
        c2_email_id = result_data['subcreated'][1]['contact']['emails'][0]['handle_id']
        c3_handle_id = result_data['subcreated'][2]['contact']['handle_id']
        c3_email_id = result_data['subcreated'][2]['contact']['emails'][0]['handle_id']
        c3_phone_id = result_data['subcreated'][2]['contact']['phones'][0]['handle_id']

        # check the integrity of the data
        created_data = result_data['created']['group']

        # check group
        assert created_data['name'] == group_name, \
            "Group name doesn't match \n{} != {}"\
                .format(created_data['name'], group_name)
        assert created_data['description'] == description_group, \
            "Group name doesn't match \n{} != {}"\
                .format(created_data['description'], description_group)

        # check members
        subcreated_data = result_data['subcreated']

        # first contact
        assert subcreated_data[0]['contact']['first_name'] == c1_first_name, \
            "1st contact's first name doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['first_name'], c1_first_name)
        assert subcreated_data[0]['contact']['last_name'] == c1_last_name, \
            "1st contact's last name doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['last_name'], c1_last_name)
        assert subcreated_data[0]['contact']['emails'][0]['name'] == c1_mail, \
            "1st contact's email doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['emails'][0]['name'], c1_mail)
        assert subcreated_data[0]['contact']['phones'][0]['name'] == c1_phone, \
            "1st contact's phone doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['phones'][0]['name'], c1_phone)
        assert subcreated_data[0]['contact']['member_of_groups'][0]['name'] == group_name, \
            "1st contact's group name doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['member_of_groups'][0]['name'], group_name)

        # second contact
        assert subcreated_data[1]['contact']['first_name'] == c2_first_name, \
            "2nd contact's first name doesn't match \n{} != {}"\
                .format(subcreated_data[1]['contact']['first_name'], c2_first_name)
        assert subcreated_data[1]['contact']['last_name'] == c2_last_name, \
            "2nd contact's last name doesn't match \n{} != {}"\
                .format(subcreated_data[1]['contact']['last_name'], c2_last_name)
        assert subcreated_data[1]['contact']['emails'][0]['name'] == c2_mail, \
            "2nd contact's email doesn't match \n{} != {}"\
                .format(subcreated_data[1]['contact']['emails'][0]['name'], c2_mail)
        assert subcreated_data[1]['contact']['member_of_groups'][0]['name'] == group_name, \
            "2nd contact's group name doesn't match \n{} != {}"\
                .format(subcreated_data[1]['contact']['member_of_groups'][0]['name'], group_name)

        # third contact
        assert subcreated_data[2]['contact']['first_name'] == c3_first_name, \
            "3rd contact's first name doesn't match \n{} != {}"\
                .format(subcreated_data[2]['contact']['first_name'], c3_first_name)
        assert subcreated_data[2]['contact']['last_name'] == c3_last_name, \
            "3rd contact's last name doesn't match \n{} != {}"\
                .format(subcreated_data[2]['contact']['last_name'], c3_last_name)
        assert subcreated_data[2]['contact']['emails'][0]['name'] == c3_mail, \
            "3rd contact's email doesn't match \n{} != {}"\
                .format(subcreated_data[2]['contact']['emails'][0]['name'], c3_mail)
        assert subcreated_data[2]['contact']['phones'][0]['name'] == c3_phone, \
            "3rd contact's phone doesn't match \n{} != {}"\
                .format(subcreated_data[2]['contact']['phones'][0]['name'], c3_phone)
        assert subcreated_data[2]['contact']['member_of_groups'][0]['name'] == group_name, \
            "3rd contact's group name doesn't match \n{} != {}"\
                .format(subcreated_data[2]['contact']['member_of_groups'][0]['name'], group_name)

        ## edit
        group_name = "The Beach Boys"
        c1_mail = 'bwilson@beachboys.com'
        c1_phone = '555-123456'
        c2_mail = 'mlove@beachboys.com'
        c2_phone = '555-987654'
        phone_type2 = 'personal'

        c4_first_name = "Carl"
        c4_last_name = "Wilson"
        c4_mail = 'cwilson@beachboys.com'
        c4_phone = '555-000000'

        # Update query

        query = '''
        mutation {{
          composite_group(input: {{
            update_input: {{
              handle_id: {group_handle_id},
              name: "{group_name}"
              description: "{description_group}"
          	}}
            create_subinputs:[
              {{
                first_name: "{c4_first_name}"
                last_name: "{c4_last_name}"
                contact_type: "{contact_type}"
                email: "{c4_mail}"
                email_type: "{email_type}"
                phone: "{c4_phone}"
                phone_type: "{phone_type2}"
              }}
            ]
            update_subinputs:[
              {{
                handle_id: {c1_handle_id}
                first_name: "{c1_first_name}"
                last_name: "{c1_last_name}"
                contact_type: "{contact_type}"
                email_handle_id: {c1_email_id}
                email: "{c1_mail}"
                email_type: "{email_type}"
                email_handle_id: {c1_email_id}
                phone: "{c1_phone}"
                phone_type: "{phone_type2}"
                phone_handle_id: {c1_phone_id}
              }}
              {{
                handle_id: {c2_handle_id}
                first_name: "{c2_first_name}"
                last_name: "{c2_last_name}"
                contact_type: "{contact_type}"
                email_handle_id: {c2_email_id}
                email: "{c2_mail}"
                email_type: "{email_type}"
                phone: "{c2_phone}"
                phone_type: "{phone_type2}"
              }}
            ]
            delete_subinputs:[
              {{
                handle_id: {c3_handle_id}
              }}
            ]
          }})
          {{
            updated{{
              errors{{
                field
                messages
              }}
              group{{
                handle_id
                name
                description
              }}
            }}
            subcreated{{
              errors{{
                field
                messages
              }}
              contact{{
                handle_id
                first_name
                last_name
                emails{{
                  handle_id
                  name
                  type
                }}
                phones{{
                  handle_id
                  name
                  type
                }}
                member_of_groups{{
                  name
                }}
              }}
            }}
            subupdated{{
              errors{{
                field
                messages
              }}
              contact{{
                handle_id
                first_name
                last_name
                emails{{
                  handle_id
                  name
                  type
                }}
                phones{{
                  handle_id
                  name
                  type
                }}
                member_of_groups{{
                  name
                }}
              }}
            }}
            subdeleted{{
              errors{{
                field
                messages
              }}
              success
            }}
          }}
        }}
        '''.format(group_handle_id=group_handle_id, group_name=group_name,
                    description_group=description_group,
                    c4_first_name=c4_first_name, c4_last_name=c4_last_name,
                    contact_type=contact_type, c4_mail=c4_mail,
                    email_type=email_type, c4_phone=c4_phone,
                    phone_type2=phone_type2, c1_handle_id=c1_handle_id,
                    c1_first_name=c1_first_name, c1_last_name=c1_last_name,
                    c1_email_id=c1_email_id, c1_mail=c1_mail,
                    c1_phone=c1_phone, c1_phone_id=c1_phone_id,
                    c2_handle_id=c2_handle_id, c2_first_name=c2_first_name,
                    c2_last_name=c2_last_name, c2_email_id=c2_email_id,
                    c2_mail=c2_mail, c2_phone=c2_phone, c3_handle_id=c3_handle_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = result.data['composite_group']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        for subcreated in result.data['composite_group']['subcreated']:
            assert not subcreated['errors']

        for subupdated in result.data['composite_group']['subupdated']:
            assert not subupdated['errors']

        for subdeleted in result.data['composite_group']['subdeleted']:
            assert not subdeleted['errors']

        # get the ids
        result_data = result.data['composite_group']
        c4_handle_id = result_data['subcreated'][0]['contact']['handle_id']

        # check the integrity of the data
        updated_data = result_data['updated']['group']

        # check group
        assert updated_data['name'] == group_name, \
            "Group name doesn't match \n{} != {}"\
                .format(updated_data['name'], group_name)
        assert updated_data['description'] == description_group, \
            "Group name doesn't match \n{} != {}"\
                .format(updated_data['description'], description_group)

        # check members
        subcreated_data = result_data['subcreated']
        subupdated_data = result_data['subupdated']
        subdeleted_data = result_data['subdeleted']

        # fourth contact
        assert subcreated_data[0]['contact']['first_name'] == c4_first_name, \
            "4th contact's first name doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['first_name'], c4_first_name)
        assert subcreated_data[0]['contact']['last_name'] == c4_last_name, \
            "4th contact's last name doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['last_name'], c4_last_name)
        assert subcreated_data[0]['contact']['emails'][0]['name'] == c4_mail, \
            "4th contact's email doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['emails'][0]['name'], c4_mail)
        assert subcreated_data[0]['contact']['phones'][0]['name'] == c4_phone, \
            "4th contact's phone doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['phones'][0]['name'], c4_phone)
        assert subcreated_data[0]['contact']['member_of_groups'][0]['name'] == group_name, \
            "4th contact's group name doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['member_of_groups'][0]['name'], group_name)

        # first contact
        assert subupdated_data[0]['contact']['first_name'] == c1_first_name, \
            "1st contact's first name doesn't match \n{} != {}"\
                .format(subupdated_data[0]['contact']['first_name'], c1_first_name)
        assert subupdated_data[0]['contact']['last_name'] == c1_last_name, \
            "1st contact's last name doesn't match \n{} != {}"\
                .format(subupdated_data[0]['contact']['last_name'], c1_last_name)
        assert subupdated_data[0]['contact']['emails'][0]['name'] == c1_mail, \
            "1st contact's email doesn't match \n{} != {}"\
                .format(subupdated_data[0]['contact']['emails'][0]['name'], c1_mail)
        assert subupdated_data[0]['contact']['phones'][0]['name'] == c1_phone, \
            "1st contact's phone doesn't match \n{} != {}"\
                .format(subupdated_data[0]['contact']['phones'][0]['name'], c1_phone)
        assert subupdated_data[0]['contact']['member_of_groups'][0]['name'] == group_name, \
            "1st contact's group name doesn't match \n{} != {}"\
                .format(subupdated_data[0]['contact']['member_of_groups'][0]['name'], group_name)

        # second contact
        assert subupdated_data[1]['contact']['first_name'] == c2_first_name, \
            "2nd contact's first name doesn't match \n{} != {}"\
                .format(subupdated_data[1]['contact']['first_name'], c2_first_name)
        assert subupdated_data[1]['contact']['last_name'] == c2_last_name, \
            "2nd contact's last name doesn't match \n{} != {}"\
                .format(subupdated_data[1]['contact']['last_name'], c2_last_name)
        assert subupdated_data[1]['contact']['emails'][0]['name'] == c2_mail, \
            "2nd contact's email doesn't match \n{} != {}"\
                .format(subupdated_data[1]['contact']['emails'][0]['name'], c2_mail)
        assert subupdated_data[1]['contact']['phones'][0]['name'] == c2_phone, \
            "1st contact's phone doesn't match \n{} != {}"\
                .format(subupdated_data[1]['contact']['phones'][0]['name'], c2_phone)
        assert subupdated_data[1]['contact']['member_of_groups'][0]['name'] == group_name, \
            "2nd contact's group name doesn't match \n{} != {}"\
                .format(subupdated_data[1]['contact']['member_of_groups'][0]['name'], group_name)

        # third contact
        assert subdeleted_data[0]['success'], "The requested contact couldn't be deleted"


class OrganizationComplexTest(Neo4jGraphQLTest):
    def test_composite_organization(self):
        org_name = "PyPI"
        org_type = "partner"
        org_id = "AABA"
        parent_org_id = self.organization1.handle_id
        org_web = "pypi.org"
        org_num = "55446"

        contact_type = "person"
        email_type = "work"
        phone_type = "work"

        c1_first_name = "Janet"
        c1_last_name  = "Doe"
        c1_email = "jdoe@pypi.org"
        c1_phone = "+34600123456"

        c2_first_name = "Brian"
        c2_last_name  = "Smith"
        c2_email = "bsmith@pypi.org"
        c2_phone = "+34600789456"

        org_addr_name = "Main"
        org_addr_st = "Fake St. 123"
        org_addr_pcode = "21500"
        org_addr_parea = "Huelva"

        org_addr_name2 = "Second"
        org_addr_st2 = "Real St. 456"
        org_addr_pcode2 = "41000"
        org_addr_parea2 = "Sevilla"

        # Create query

        query = '''
        mutation{{
          composite_organization(input:{{
            create_input:{{
              name: "{org_name}"
              type: "{org_type}"
              affiliation_site_owner: true
              organization_id: "{org_id}"
              relationship_parent_of: {parent_org_id}
              website: "{org_web}"
              organization_number: "{org_num}"
            }}
            create_subinputs:[
              {{
                first_name: "{c1_first_name}"
                last_name: "{c1_last_name}"
                contact_type: "{contact_type}"
                email: "{c1_email}"
                email_type: "{email_type}"
                phone:"{c1_phone}"
                phone_type: "{phone_type}"
              }}
              {{
                first_name: "{c2_first_name}"
                last_name: "{c2_last_name}"
                contact_type: "{contact_type}"
                email: "{c2_email}"
                email_type: "{email_type}"
                phone:"{c2_phone}"
                phone_type: "{phone_type}"
              }}
            ]
            create_address:[
              {{
                name: "{org_addr_name}"
                street: "{org_addr_st}"
                postal_code: "{org_addr_pcode}"
                postal_area: "{org_addr_parea}"
              }}
              {{
                name: "{org_addr_name2}"
                street: "{org_addr_st2}"
                postal_code: "{org_addr_pcode2}"
                postal_area: "{org_addr_parea2}"
              }}
            ]
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              organization{{
                handle_id
                type
                name
                description
                addresses{{
                  handle_id
                  name
                  street
                  postal_code
                  postal_area
                }}
                contacts{{
                  handle_id
                  first_name
                  last_name
                  contact_type
                  emails{{
                    handle_id
                    name
                    type
                  }}
                  phones{{
                    handle_id
                    name
                    type
                  }}
                }}
              }}
            }}
            subcreated{{
              errors{{
                field
                messages
              }}
              contact{{
                handle_id
                first_name
                last_name
                contact_type
                emails{{
                  handle_id
                  name
                  type
                }}
                phones{{
                  handle_id
                  name
                  type
                }}
                organizations{{
                  handle_id
                  name
                }}
                roles{{
                  relation_id
                  name
                  start{{
                    handle_id
                    first_name
                    last_name
                  }}
                  end{{
                    handle_id
                    name
                  }}
                }}
              }}
            }}
            address_created{{
              errors{{
                field
                messages
              }}
              address{{
                handle_id
                name
                street
                postal_code
                postal_area
              }}
            }}
          }}
        }}
        '''.format(org_name=org_name, org_type=org_type, org_id=org_id,
                    parent_org_id=parent_org_id, org_web=org_web, org_num=org_num,
                    c1_first_name=c1_first_name, c1_last_name=c1_last_name,
                    contact_type=contact_type, c1_email=c1_email,
                    email_type=email_type, c1_phone=c1_phone,
                    phone_type=phone_type, c2_first_name=c2_first_name,
                    c2_last_name=c2_last_name, c2_email=c2_email,
                    c2_phone=c2_phone, org_addr_name=org_addr_name,
                    org_addr_st=org_addr_st, org_addr_pcode=org_addr_pcode,
                    org_addr_parea=org_addr_parea, org_addr_name2=org_addr_name2,
                    org_addr_st2=org_addr_st2, org_addr_pcode2=org_addr_pcode2,
                    org_addr_parea2=org_addr_parea2)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_organization']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        for subcreated in result.data['composite_organization']['subcreated']:
            assert not subcreated['errors']

        for subcreated in result.data['composite_organization']['address_created']:
            assert not subcreated['errors']

        # get the ids
        result_data = result.data['composite_organization']
        organization_handle_id = result_data['created']['organization']['handle_id']
        c1_handle_id = result_data['subcreated'][0]['contact']['handle_id']
        c1_email_id = result_data['subcreated'][0]['contact']['emails'][0]['handle_id']
        c1_phone_id = result_data['subcreated'][0]['contact']['phones'][0]['handle_id']
        c1_org_rel_id = result_data['subcreated'][0]['contact']['roles'][0]['relation_id']
        c2_handle_id = result_data['subcreated'][1]['contact']['handle_id']
        address1_id = result_data['address_created'][0]['address']['handle_id']
        address2_id = result_data['address_created'][1]['address']['handle_id']

        # check the integrity of the data
        created_data = result_data['created']['organization']

        # check organization
        assert created_data['name'] == org_name, \
            "Organization name doesn't match \n{} != {}"\
                .format(created_data['name'], org_name)
        assert created_data['type'] == org_type, \
            "Organization type doesn't match \n{} != {}"\
                .format(created_data['type'], org_type)

        # check subnodes
        # address
        address_node = created_data['addresses'][0]
        assert address_node['name'] == org_addr_name, \
            "Address' name doesn't match \n{} != {}"\
                .format(address_node['name'], org_addr_name)
        assert address_node['street'] == org_addr_st, \
            "Address' street doesn't match \n{} != {}"\
                .format(address_node['street'], org_addr_st)
        assert address_node['postal_code'] == org_addr_pcode, \
            "Address' postal code doesn't match \n{} != {}"\
                .format(address_node['postal_code'], org_addr_pcode)
        assert address_node['postal_area'] == org_addr_parea, \
            "Address' postal area doesn't match \n{} != {}"\
                .format(address_node['postal_area'], org_addr_parea)

        address_node = created_data['addresses'][1]
        assert address_node['name'] == org_addr_name2, \
            "Address' 2 name doesn't match \n{} != {}"\
                .format(address_node['name'], org_addr_name2)
        assert address_node['street'] == org_addr_st2, \
            "Address' 2 street doesn't match \n{} != {}"\
                .format(address_node['street'], org_addr_st2)
        assert address_node['postal_code'] == org_addr_pcode2, \
            "Address' 2 postal code doesn't match \n{} != {}"\
                .format(address_node['postal_code'], org_addr_pcode2)
        assert address_node['postal_area'] == org_addr_parea2, \
            "Address' 2 postal area doesn't match \n{} != {}"\
                .format(address_node['postal_area'], org_addr_parea2)

        # contacts
        subcreated_data = result_data['subcreated']

        assert subcreated_data[0]['contact']['first_name'] == c1_first_name, \
            "1st contact's first name doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['first_name'], c1_first_name)
        assert subcreated_data[0]['contact']['last_name'] == c1_last_name, \
            "1st contact's last name doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['last_name'], c1_last_name)
        assert subcreated_data[0]['contact']['emails'][0]['name'] == c1_email, \
            "1st contact's email doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['emails'][0]['name'], c1_email)
        assert subcreated_data[0]['contact']['phones'][0]['name'] == c1_phone, \
            "1st contact's phone doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['phones'][0]['name'], c1_phone)
        assert subcreated_data[0]['contact']['organizations'][0]['name'] == org_name, \
            "1st contact's organization name doesn't match \n{} != {}"\
                .format(subcreated_data[0]['contact']['organizations'][0]['name'], org_name)

        assert subcreated_data[1]['contact']['first_name'] == c2_first_name, \
            "2nd contact's first name doesn't match \n{} != {}"\
                .format(subcreated_data[1]['contact']['first_name'], c2_first_name)
        assert subcreated_data[1]['contact']['last_name'] == c2_last_name, \
            "2nd contact's last name doesn't match \n{} != {}"\
                .format(subcreated_data[1]['contact']['last_name'], c2_last_name)
        assert subcreated_data[1]['contact']['emails'][0]['name'] == c2_email, \
            "2nd contact's email doesn't match \n{} != {}"\
                .format(subcreated_data[1]['contact']['emails'][0]['name'], c2_email)
        assert subcreated_data[1]['contact']['phones'][0]['name'] == c2_phone, \
            "2nd contact's phone doesn't match \n{} != {}"\
                .format(subcreated_data[1]['contact']['phones'][0]['name'], c2_phone)
        assert subcreated_data[1]['contact']['organizations'][0]['name'] == org_name, \
            "2nd contact's organization name doesn't match \n{} != {}"\
                .format(subcreated_data[1]['contact']['organizations'][0]['name'], org_name)

        # Update query
        org_name = 'FSF'
        c1_email = "jdoe@fsf.org"
        c2_email = "bsmith@fsf.org"

        c3_first_name = "Stella"
        c3_last_name  = "Svennson"
        c3_email = "ssvensson@fsf.org"
        c3_phone = "+34600555123"

        org_addr_name3 = "Thrid"
        org_addr_st3 = "Imaginary St. 789"
        org_addr_pcode3 = "41001"
        org_addr_parea3 = "Sevilla"

        nondefault_role = Role.objects.all().first()
        nondefault_roleid = nondefault_role.handle_id

        query = '''
        mutation{{
          composite_organization(input:{{
            update_input: {{
              handle_id: {org_handle_id}
              name: "{org_name}"
              type: "{org_type}"
              affiliation_site_owner: false
              affiliation_partner: true
              organization_id: "{org_id}"
              website: "{org_web}"
              organization_number: "{org_num}"
            }}
            create_subinputs:[{{
              first_name: "{c3_first_name}"
              last_name: "{c3_last_name}"
              contact_type: "{contact_type}"
              email: "{c3_email}"
              email_type: "{email_type}"
              phone: "{c3_phone}"
              phone_type: "{phone_type}"
              role_handle_id: {nondefault_roleid}
            }}]
            update_subinputs:[{{
              handle_id: {c1_handle_id}
              first_name: "{c1_first_name}"
              last_name: "{c1_last_name}"
              contact_type: "{contact_type}"
              email: "{c1_email}"
              email_type: "{email_type}"
              email_handle_id: {c1_email_id}
              phone: "{c1_phone}"
              phone_type: "{phone_type}"
              role_handle_id: {nondefault_roleid}
            }}]
            delete_subinputs:[{{
              handle_id: {c2_handle_id}
            }}]
            create_address:[{{
              name: "{org_addr_name3}"
              street: "{org_addr_st3}"
              postal_code: "{org_addr_pcode3}"
              postal_area: "{org_addr_parea3}"
            }}]
            update_address:[{{
              handle_id: {address1_id}
              name: "{org_addr_name}"
              street: "{org_addr_st}"
              postal_code: "{org_addr_pcode}"
              postal_area: "{org_addr_parea}"
            }}]
            delete_address:[{{
              handle_id: {address2_id}
            }}]
            unlink_subinputs:[{{
              relation_id: {c1_org_rel_id}
            }}]
          }}){{
            updated{{
            	errors{{
                field
                messages
              }}
              organization{{
                handle_id
                type
                name
                description
                addresses{{
                  handle_id
                  name
                  street
                  postal_code
                  postal_area
                }}
                contacts{{
                  handle_id
                  first_name
                  last_name
                  contact_type
                  emails{{
                    handle_id
                    name
                    type
                  }}
                  phones{{
                    handle_id
                    name
                    type
                  }}
                  organizations{{
                    handle_id
                    name
                  }}
                  roles{{
                    relation_id
                    name
                    start{{
                      handle_id
                      first_name
                      last_name
                    }}
                    end{{
                      handle_id
                      name
                    }}
                  }}
                }}
              }}
          	}}
            subcreated{{
              errors{{
                field
                messages
              }}
              contact{{
                handle_id
                first_name
                last_name
                contact_type
                emails{{
                  handle_id
                  name
                  type
                }}
                phones{{
                  handle_id
                  name
                  type
                }}
                organizations{{
                  handle_id
                  name
                }}
                roles{{
                  relation_id
                  name
                  start{{
                    handle_id
                    first_name
                    last_name
                  }}
                  end{{
                    handle_id
                    name
                  }}
                }}
              }}
            }}
            subupdated{{
              errors{{
                field
                messages
              }}
              contact{{
                handle_id
                first_name
                last_name
                contact_type
                emails{{
                  handle_id
                  name
                  type
                }}
                phones{{
                  handle_id
                  name
                  type
                }}
                organizations{{
                  handle_id
                  name
                }}
                roles{{
                  relation_id
                  name
                  start{{
                    handle_id
                    first_name
                    last_name
                  }}
                  end{{
                    handle_id
                    name
                  }}
                }}
              }}
            }}
            subdeleted{{
              errors{{
                field
                messages
              }}
              success
            }}
            address_created{{
              errors{{
                field
                messages
              }}
              address{{
                handle_id
                name
                street
                postal_code
                postal_area
              }}
            }}
            address_updated{{
              errors{{
                field
                messages
              }}
              address{{
                handle_id
                name
                street
                postal_code
                postal_area
              }}
            }}
            address_deleted{{
              errors{{
                field
                messages
              }}
              success
            }}
          }}
        }}
        '''.format(org_handle_id=organization_handle_id, org_name=org_name,
                    org_type=org_type, org_id=org_id, org_web=org_web,
                    org_num=org_num, c3_first_name=c3_first_name,
                    c3_last_name=c3_last_name, contact_type=contact_type,
                    c3_email=c3_email, email_type=email_type, c3_phone=c3_phone,
                    phone_type=phone_type, nondefault_roleid=nondefault_roleid,
                    c1_handle_id=c1_handle_id, c1_first_name=c1_first_name,
                    c1_last_name=c1_last_name, c1_email=c1_email,
                    c1_email_id=c1_email_id, c1_phone=c1_phone,
                    c2_handle_id=c2_handle_id, org_addr_name3=org_addr_name3,
                    org_addr_st3=org_addr_st3, org_addr_pcode3=org_addr_pcode3,
                    org_addr_parea3=org_addr_parea3, address1_id=address1_id,
                    org_addr_name=org_addr_name, org_addr_st=org_addr_st,
                    org_addr_pcode=org_addr_pcode, org_addr_parea=org_addr_parea,
                    address2_id=address2_id, c1_org_rel_id=c1_org_rel_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = result.data['composite_organization']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        for subcreated in result.data['composite_organization']['subcreated']:
            assert not subcreated['errors']

        for subupdated in result.data['composite_organization']['subupdated']:
            assert not subupdated['errors']

        for subdeleted in result.data['composite_organization']['subdeleted']:
            assert not subdeleted['errors']

        for subcreated in result.data['composite_organization']['address_created']:
            assert not subcreated['errors']

        for subupdated in result.data['composite_organization']['address_updated']:
            assert not subupdated['errors']

        for subdeleted in result.data['composite_organization']['address_deleted']:
            assert not subdeleted['errors']

        # get the ids
        result_data = result.data['composite_organization']
        address3_id = result_data['address_created'][0]['address']['handle_id']
        c3_handle_id = result_data['subcreated'][0]['contact']['handle_id']

        # check the integrity of the data
        updated_data = result_data['updated']['organization']

        # check organization
        assert updated_data['name'] == org_name, \
            "Organization name doesn't match \n{} != {}"\
                .format(updated_data['name'], org_name)
        assert updated_data['type'] == org_type, \
            "Organization type doesn't match \n{} != {}"\
                .format(updated_data['type'], org_type)

        # check subnodes (address and contacts)
        address_node_1 = None
        address_node_3 = None

        for address_node in updated_data['addresses']:
            if address_node['handle_id'] == address1_id:
                address_node_1 = address_node
            elif address_node['handle_id'] == address3_id:
                address_node_3 = address_node

        self.assertIsNotNone(address_node_1)

        assert address_node_1['name'] == org_addr_name, \
            "Created address' name doesn't match \n{} != {}"\
                .format(address_node_1['name'], org_addr_name)
        assert address_node_1['street'] == org_addr_st, \
            "Created address' street doesn't match \n{} != {}"\
                .format(address_node_1['street'], org_addr_st)
        assert address_node_1['postal_code'] == org_addr_pcode, \
            "Created address' postal code doesn't match \n{} != {}"\
                .format(address_node_1['postal_code'], org_addr_pcode)
        assert address_node_1['postal_area'] == org_addr_parea, \
            "Created address' postal area doesn't match \n{} != {}"\
                .format(address_node_1['postal_area'], org_addr_parea)

        self.assertIsNotNone(address_node_3)

        assert address_node_3['name'] == org_addr_name3, \
            "Created address' name doesn't match \n{} != {}"\
                .format(address_node_3['name'], org_addr_name3)
        assert address_node_3['street'] == org_addr_st3, \
            "Created address' street doesn't match \n{} != {}"\
                .format(address_node_3['street'], org_addr_st3)
        assert address_node_3['postal_code'] == org_addr_pcode3, \
            "Created address' postal code doesn't match \n{} != {}"\
                .format(address_node_3['postal_code'], org_addr_pcode3)
        assert address_node_3['postal_area'] == org_addr_parea3, \
            "Created address' postal area doesn't match \n{} != {}"\
                .format(address_node_3['postal_area'], org_addr_parea3)

        contact_1 = None
        contact_3 = None

        for contact_node in updated_data['contacts']:
            if contact_node['handle_id'] == c1_handle_id:
                contact_1 = contact_node
            elif contact_node['handle_id'] == c3_handle_id:
                contact_3 = contact_node

        self.assertIsNotNone(contact_1)
        assert contact_1['first_name'] == c1_first_name, \
            "1st contact's first name doesn't match \n{} != {}"\
                .format(contact_1['first_name'], c1_first_name)
        assert contact_1['last_name'] == c1_last_name, \
            "1st contact's last name doesn't match \n{} != {}"\
                .format(contact_1['last_name'], c1_last_name)
        assert contact_1['emails'][0]['name'] == c1_email, \
            "1st contact's email doesn't match \n{} != {}"\
                .format(contact_1['emails'][0]['name'], c1_email)
        assert contact_1['phones'][0]['name'] == c1_phone, \
            "1st contact's phone doesn't match \n{} != {}"\
                .format(contact_1['phones'][0]['name'], c1_phone)
        assert contact_1['organizations'][0]['name'] == org_name, \
            "1st contact's organization name doesn't match \n{} != {}"\
                .format(contact_1['organizations'][0]['name'], org_name)
        assert contact_1['roles'][0]['name'] == nondefault_role.name, \
            "1st contact's role name doesn't match \n{} != {}"\
                .format(contact_1['roles'][0]['name'], nondefault_role.name)
        assert len(contact_1['roles']) == 1, "1st contact has two roles"

        self.assertIsNotNone(contact_3)
        assert contact_3['first_name'] == c3_first_name, \
            "3rd contact's first name doesn't match \n{} != {}"\
                .format(contact_3['first_name'], c3_first_name)
        assert contact_3['last_name'] == c3_last_name, \
            "3rd contact's last name doesn't match \n{} != {}"\
                .format(contact_3['last_name'], c3_last_name)
        assert contact_3['emails'][0]['name'] == c3_email, \
            "3rd contact's email doesn't match \n{} != {}"\
                .format(contact_3['emails'][0]['name'], c3_email)
        assert contact_3['phones'][0]['name'] == c3_phone, \
            "3rd contact's phone doesn't match \n{} != {}"\
                .format(contact_3['phones'][0]['name'], c3_phone)
        assert contact_3['organizations'][0]['name'] == org_name, \
            "3rd contact's organization name doesn't match \n{} != {}"\
                .format(contact_3['organizations'][0]['name'], org_name)
        assert contact_3['roles'][0]['name'] == nondefault_role.name, \
            "3rd contact's role name doesn't match \n{} != {}"\
                .format(contact_3['roles'][0]['name'], nondefault_role.name)
        assert len(contact_3['roles']) == 1, "1st contact has two roles"

        # check for deleted address and contact
        c2_handle_id = int(c2_handle_id)
        assert not NodeHandle.objects.filter(handle_id=c2_handle_id).exists(), \
            "Second contact of this organization should have been deleted"

        address2_id = int(address2_id)
        assert not NodeHandle.objects.filter(handle_id=address2_id).exists(), \
            "Second address of this organization should have been deleted"


class ContactsComplexTest(Neo4jGraphQLTest):
    def test_multiple_mutation(self):
        c1_first_name = "Jane"
        c1_last_name  = "Doe"
        c1_contact_type = "person"
        c1_email = "jdoe@pypi.org"
        c1_email_type = "work"
        c2_email = "jdoe@myemail.org"
        c2_email_type = "personal"
        c1_phone = "+34600123456"
        c1_phone_type = "work"
        c2_phone = "+34600789456"
        c2_phone_type = "personal"

        role_handle_id = Role.objects.all().first().handle_id
        organization_id = self.organization1.handle_id

        query = '''
        mutation{{
          composite_contact(input:{{
            create_input:{{
              first_name: "{c1_first_name}"
              last_name: "{c1_last_name}"
              contact_type: "{c1_contact_type}"
            }}
            create_subinputs:[
              {{
                name: "{c1_email}"
                type: "{c1_email_type}"
              }}
              {{
                name: "{c2_email}"
                type: "{c2_email_type}"
              }}
            ]
            create_phones:[
              {{
                name: "{c1_phone}"
                type: "{c1_phone_type}"
              }}
              {{
                name: "{c2_phone}"
                type: "{c2_phone_type}"
              }}
            ]
            link_rolerelations:[
              {{
                role_handle_id: {role_handle_id}
                organization_handle_id: {organization_id}
              }}
            ]
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              contact{{
                handle_id
                first_name
                last_name
                contact_type
                emails{{
                  handle_id
                  name
                  type
                }}
                phones{{
                  handle_id
                  name
                  type
                }}
              }}
            }}
            subcreated{{
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
            phones_created{{
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
            rolerelations{{
              errors{{
                field
                messages
              }}
              rolerelation{{
                relation_id
                type
                start{{
                  handle_id
                  first_name
                  last_name
                }}
                end{{
                  handle_id
                  name
                }}
              }}
            }}
          }}
        }}
        '''.format(c1_first_name=c1_first_name, c1_last_name=c1_last_name,
                    c1_contact_type=c1_contact_type, c1_email=c1_email,
                    c1_email_type=c1_email_type, c2_email=c2_email,
                    c2_email_type=c2_email_type, c1_phone=c1_phone,
                    c1_phone_type=c1_phone_type, c2_phone=c2_phone,
                    c2_phone_type=c2_phone_type, role_handle_id=role_handle_id,
                    organization_id=organization_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_contact']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        for subcreated in result.data['composite_contact']['subcreated']:
            assert not subcreated['errors']

        for subcreated in result.data['composite_contact']['phones_created']:
            assert not subcreated['errors']

        for subcreated in result.data['composite_contact']['rolerelations']:
            assert not subcreated['errors']

        # get the ids
        result_data = result.data['composite_contact']
        c1_handle_id = result_data['created']['contact']['handle_id']
        c1_email_id = result_data['subcreated'][0]['email']['handle_id']
        c1_email_id2 = result_data['subcreated'][1]['email']['handle_id']
        c1_phone_id = result_data['phones_created'][0]['phone']['handle_id']
        c1_phone_id2 = result_data['phones_created'][1]['phone']['handle_id']
        role_relation_id = result_data['rolerelations'][0]['rolerelation']['relation_id']

        # check the integrity of the data
        created_data = result_data['created']['contact']

        # check contact
        assert created_data['first_name'] == c1_first_name, \
            "1st contact's first name doesn't match \n{} != {}"\
                .format(created_data['first_name'], c1_first_name)
        assert created_data['last_name'] == c1_last_name, \
            "1st contact's last name doesn't match \n{} != {}"\
                .format(created_data['last_name'], c1_last_name)

        # check email
        created_email_data = result_data['subcreated'][0]['email']

        assert c1_email_id == created_data['emails'][0]['handle_id'], \
            "Contact's email handle_id doesn't match \n{} != {}"\
                .format(c1_email_id, created_data['emails'][0]['handle_id'])
        assert c1_email == created_email_data['name'], \
            "Contact's email doesn't match \n{} != {}"\
                .format(c1_email, created_email_data['name'])
        assert c1_email_type == created_email_data['type'], \
            "Contact's email type doesn't match \n{} != {}"\
                .format(c1_email_type, created_email_data['type'])

        created_email_data = result_data['subcreated'][1]['email']

        assert c1_email_id2 == created_data['emails'][1]['handle_id'], \
            "Contact's email handle_id doesn't match \n{} != {}"\
                .format(c1_email_id2, created_data['emails'][1]['handle_id'])
        assert c2_email == created_email_data['name'], \
            "Contact's email doesn't match \n{} != {}"\
                .format(c2_email, created_email_data['name'])
        assert c2_email_type == created_email_data['type'], \
            "Contact's email type doesn't match \n{} != {}"\
                .format(c2_email_type, created_email_data['type'])

        # check phone
        created_phone_data = result_data['phones_created'][0]['phone']

        assert c1_phone_id == created_data['phones'][0]['handle_id'], \
            "Contact's phone handle_id doesn't match \n{} != {}"\
                .format(c1_phone_id, created_data['phones'][0]['handle_id'])
        assert c1_phone == created_phone_data['name'], \
            "Contact's phone doesn't match \n{} != {}"\
                .format(c1_phone, created_phone_data['name'])
        assert c1_phone_type == created_phone_data['type'], \
            "Contact's phone type doesn't match \n{} != {}"\
                .format(c1_phone_type, created_phone_data['type'])

        # check rolerelation
        rolerelation = result_data['rolerelations'][0]['rolerelation']

        assert c1_handle_id == rolerelation['start']['handle_id'], \
            "Contact's handle_id doesn't match with the one present in the relation \n\
                {} != {}".format(c1_handle_id , rolerelation['start']['handle_id'],)
        assert int(organization_id) == int(rolerelation['end']['handle_id']), \
            "Organization's handle_id doesn't match with the one present in the relation\n\
                {} != {}".format(organization_id , rolerelation['end']['handle_id'],)

        # Update mutation
        c1_first_name = "Anne"
        c1_last_name  = "Doe"
        c1_email = "adoe@pypi.org"
        c1_phone = "+34600000789"

        c3_email = "adoe@myemail.org"
        c3_email_type = "personal"
        c3_phone = "+34600111222"
        c3_phone_type = "personal"

        role_handle_id = Role.objects.all().last().handle_id
        organization_id = self.organization2.handle_id

        query = '''
        mutation{{
          composite_contact(input:{{
            update_input:{{
              handle_id: {c1_handle_id}
              first_name: "{c1_first_name}"
              last_name: "{c1_last_name}"
              contact_type: "{c1_contact_type}"
            }}
            create_subinputs:[{{
              name: "{c3_email}"
              type: "{c3_email_type}"
            }}]
            update_subinputs:[{{
              handle_id: {c1_email_id}
              name: "{c1_email}"
              type: "{c1_email_type}"
            }}]
            delete_subinputs:[{{
              handle_id: {c1_email_id2}
            }}]
            create_phones:[{{
              name: "{c3_phone}"
              type: "{c3_phone_type}"
            }}]
            update_phones:[{{
              handle_id: {c1_phone_id}
              name: "{c1_phone}"
              type: "{c1_phone_type}"
            }}]
            link_rolerelations:[{{
              role_handle_id: {role_handle_id}
              organization_handle_id: {organization_id}
            }}]
            delete_phones:[{{
              handle_id: {c1_phone_id2}
            }}]
            unlink_subinputs:[{{
              relation_id: {role_relation_id}
            }}]
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              contact{{
                handle_id
                first_name
                last_name
                contact_type
                emails{{
                  handle_id
                  name
                  type
                }}
                phones{{
                  handle_id
                  name
                  type
                }}
                roles{{
                  relation_id
                  start{{
                    handle_id
                    first_name
                  }}
                  end{{
                    handle_id
                    name
                  }}
                }}
              }}
            }}
            subcreated{{
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
            subupdated{{
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
            phones_created{{
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
            phones_updated{{
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
            rolerelations{{
              errors{{
                field
                messages
              }}
              rolerelation{{
                relation_id
                type
                start{{
                  handle_id
                  first_name
                  last_name
                }}
                end{{
                  handle_id
                  name
                }}
              }}
            }}
            unlinked{{
              success
              relation_id
            }}
          }}
        }}
        '''.format(c1_handle_id=c1_handle_id, c1_first_name=c1_first_name,
                    c1_last_name=c1_last_name, c1_contact_type=c1_contact_type,
                    c3_email=c3_email, c3_email_type=c3_email_type,
                    c1_email_id=c1_email_id, c1_email=c1_email,
                    c1_email_type=c1_email_type, c1_email_id2=c1_email_id2,
                    c3_phone=c3_phone, c3_phone_type=c3_phone_type,
                    c1_phone_id=c1_phone_id, c1_phone=c1_phone,
                    c1_phone_type=c1_phone_type, role_handle_id=role_handle_id,
                    organization_id=organization_id, c1_phone_id2=c1_phone_id2,
                    role_relation_id=role_relation_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = result.data['composite_contact']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        for subcreated in result.data['composite_contact']['subcreated']:
            assert not subcreated['errors']

        for subupdated in result.data['composite_contact']['subupdated']:
            assert not subupdated['errors']

        for subcreated in result.data['composite_contact']['phones_created']:
            assert not subcreated['errors']

        for subupdated in result.data['composite_contact']['phones_updated']:
            assert not subupdated['errors']

        for subcreated in result.data['composite_contact']['rolerelations']:
            assert not subcreated['errors']

        # get the ids
        result_data = result.data['composite_contact']
        c1_email_id3 = result_data['subcreated'][0]['email']['handle_id']
        c1_phone_id3 = result_data['phones_created'][0]['phone']['handle_id']
        role_relation_id2 = result_data['rolerelations'][0]['rolerelation']['relation_id']

        # check the integrity of the data
        updated_data = result_data['updated']['contact']

        # check contact
        assert updated_data['first_name'] == c1_first_name, \
            "1st contact's first name doesn't match \n{} != {}"\
                .format(updated_data['first_name'], c1_first_name)
        assert updated_data['last_name'] == c1_last_name, \
            "1st contact's last name doesn't match \n{} != {}"\
                .format(updated_data['last_name'], c1_last_name)

        # get emails and check them
        email1_node = None
        email3_node = None

        for email_node in updated_data['emails']:
            if email_node['handle_id'] == c1_email_id:
                email1_node = email_node
            elif email_node['handle_id'] == c1_email_id3:
                email3_node = email_node

        self.assertIsNotNone(email1_node)

        assert c1_email_id == email1_node['handle_id'], \
            "Contact's email handle_id doesn't match \n{} != {}"\
                .format(c1_email_id, email1_node['handle_id'])
        assert c1_email == email1_node['name'], \
            "Contact's email doesn't match \n{} != {}"\
                .format(c1_email, email1_node['name'])
        assert c1_email_type == email1_node['type'], \
            "Contact's email type doesn't match \n{} != {}"\
                .format(c1_email_type, email1_node['type'])

        self.assertIsNotNone(email3_node)

        assert c1_email_id3 == email3_node['handle_id'], \
            "Contact's email handle_id doesn't match \n{} != {}"\
                .format(c1_phone_id3, email3_node['handle_id'])
        assert c3_email == email3_node['name'], \
            "Contact's email doesn't match \n{} != {}"\
                .format(c3_email, email3_node['name'])
        assert c3_email_type == email3_node['type'], \
            "Contact's email type doesn't match \n{} != {}"\
                .format(c3_email_type, email3_node['type'])


        # get phones and check them
        phone1_node = None
        phone3_node = None

        for phone_node in updated_data['phones']:
            if phone_node['handle_id'] == c1_phone_id:
                phone1_node = phone_node
            elif phone_node['handle_id'] == c1_phone_id3:
                phone3_node = phone_node

        self.assertIsNotNone(phone1_node)

        assert c1_phone_id == phone1_node['handle_id'], \
            "Contact's phone handle_id doesn't match \n{} != {}"\
                .format(c1_phone_id, phone1_node['handle_id'])
        assert c1_phone == phone1_node['name'], \
            "Contact's phone doesn't match \n{} != {}"\
                .format(c1_phone, phone1_node['name'])
        assert c1_phone_type == phone1_node['type'], \
            "Contact's phone type doesn't match \n{} != {}"\
                .format(c1_phone_type, phone1_node['type'])

        self.assertIsNotNone(phone3_node)

        assert c1_phone_id3 == phone3_node['handle_id'], \
            "Contact's phone handle_id doesn't match \n{} != {}"\
                .format(c1_phone_id, phone3_node['handle_id'])
        assert c3_phone == phone3_node['name'], \
            "Contact's phone doesn't match \n{} != {}"\
                .format(c3_phone, phone3_node['name'])
        assert c3_phone_type == phone3_node['type'], \
            "Contact's phone type doesn't match \n{} != {}"\
                .format(c3_phone_type, phone3_node['type'])

        # check rolerelation
        assert len(result_data['rolerelations']) == 1, \
            'This contact should only have one role'
        rolerelation = result_data['rolerelations'][0]['rolerelation']

        assert c1_handle_id == rolerelation['start']['handle_id'], \
            "Contact's handle_id doesn't match with the one present in the relation \n\
                {} != {}".format(c1_handle_id , rolerelation['start']['handle_id'],)
        assert int(organization_id) == int(rolerelation['end']['handle_id']), \
            "Organization's handle_id doesn't match with the one present in the relation\n\
                {} != {}".format(organization_id , rolerelation['end']['handle_id'],)

        # check for deleted email and phone
        c1_email_id2 = int(c1_email_id2)
        assert not NodeHandle.objects.filter(handle_id=c1_email_id2).exists(), \
            "This email node should had been deleted"

        c1_phone_id2 = int(c1_phone_id2)
        assert not NodeHandle.objects.filter(handle_id=c1_phone_id2).exists(), \
            "This phone node should had been deleted"

    def test_multiple_mutation_2(self):
        c1_first_name = "Jane"
        c1_last_name  = "Doe"
        c1_contact_type = "person"
        c1_email = "jdoe@pypi.org"
        c1_email_type = "work"
        c2_email = "jdoe@myemail.org"
        c2_email_type = "personal"
        c1_phone = "+34600123456"
        c1_phone_type = "work"
        c2_phone = "+34600789456"
        c2_phone_type = "personal"

        role_handle_id = Role.objects.all().first().handle_id
        organization_id = self.organization1.handle_id

        query = '''
        mutation{{
          composite_contact(input:{{
            create_input:{{
              first_name: "{c1_first_name}"
              last_name: "{c1_last_name}"
              contact_type: "{c1_contact_type}"
            }}
            create_subinputs:[
              {{
                name: "{c1_email}"
                type: "{c1_email_type}"
              }}
              {{
                name: "{c2_email}"
                type: "{c2_email_type}"
              }}
            ]
            create_phones:[
              {{
                name: "{c1_phone}"
                type: "{c1_phone_type}"
              }}
              {{
                name: "{c2_phone}"
                type: "{c2_phone_type}"
              }}
            ]
            link_rolerelations:[
              {{
                role_handle_id: {role_handle_id}
                organization_handle_id: {organization_id}
              }}
            ]
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              contact{{
                handle_id
                first_name
                last_name
                contact_type
                emails{{
                  handle_id
                  name
                  type
                }}
                phones{{
                  handle_id
                  name
                  type
                }}
              }}
            }}
            subcreated{{
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
            phones_created{{
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
            rolerelations{{
              errors{{
                field
                messages
              }}
              rolerelation{{
                relation_id
                type
                start{{
                  handle_id
                  first_name
                  last_name
                }}
                end{{
                  handle_id
                  name
                }}
              }}
            }}
          }}
        }}
        '''.format(c1_first_name=c1_first_name, c1_last_name=c1_last_name,
                    c1_contact_type=c1_contact_type, c1_email=c1_email,
                    c1_email_type=c1_email_type, c2_email=c2_email,
                    c2_email_type=c2_email_type, c1_phone=c1_phone,
                    c1_phone_type=c1_phone_type, c2_phone=c2_phone,
                    c2_phone_type=c2_phone_type, role_handle_id=role_handle_id,
                    organization_id=organization_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_contact']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        for subcreated in result.data['composite_contact']['subcreated']:
            assert not subcreated['errors']

        for subcreated in result.data['composite_contact']['phones_created']:
            assert not subcreated['errors']

        # get the ids
        result_data = result.data['composite_contact']
        c1_handle_id = result_data['created']['contact']['handle_id']
        c1_email_id = result_data['subcreated'][0]['email']['handle_id']
        c1_email_id2 = result_data['subcreated'][1]['email']['handle_id']
        c1_phone_id = result_data['phones_created'][0]['phone']['handle_id']
        c1_phone_id2 = result_data['phones_created'][1]['phone']['handle_id']
        role_relation_id = result_data['rolerelations'][0]['rolerelation']['relation_id']

        # check the integrity of the data
        created_data = result_data['created']['contact']

        # check contact
        assert created_data['first_name'] == c1_first_name, \
            "1st contact's first name doesn't match \n{} != {}"\
                .format(created_data['first_name'], c1_first_name)
        assert created_data['last_name'] == c1_last_name, \
            "1st contact's last name doesn't match \n{} != {}"\
                .format(created_data['last_name'], c1_last_name)

        # check email
        created_email_data = result_data['subcreated'][0]['email']

        assert c1_email_id == created_data['emails'][0]['handle_id'], \
            "Contact's email handle_id doesn't match \n{} != {}"\
                .format(c1_email_id, created_data['emails'][0]['handle_id'])
        assert c1_email == created_email_data['name'], \
            "Contact's email doesn't match \n{} != {}"\
                .format(c1_email, created_email_data['name'])
        assert c1_email_type == created_email_data['type'], \
            "Contact's email type doesn't match \n{} != {}"\
                .format(c1_email_type, created_email_data['type'])

        created_email_data = result_data['subcreated'][1]['email']

        assert c1_email_id2 == created_data['emails'][1]['handle_id'], \
            "Contact's email handle_id doesn't match \n{} != {}"\
                .format(c1_email_id2, created_data['emails'][1]['handle_id'])
        assert c2_email == created_email_data['name'], \
            "Contact's email doesn't match \n{} != {}"\
                .format(c2_email, created_email_data['name'])
        assert c2_email_type == created_email_data['type'], \
            "Contact's email type doesn't match \n{} != {}"\
                .format(c2_email_type, created_email_data['type'])

        # check phone
        created_phone_data = result_data['phones_created'][0]['phone']

        assert c1_phone_id == created_data['phones'][0]['handle_id'], \
            "Contact's phone handle_id doesn't match \n{} != {}"\
                .format(c1_phone_id, created_data['phones'][0]['handle_id'])
        assert c1_phone == created_phone_data['name'], \
            "Contact's phone doesn't match \n{} != {}"\
                .format(c1_phone, created_phone_data['name'])
        assert c1_phone_type == created_phone_data['type'], \
            "Contact's phone type doesn't match \n{} != {}"\
                .format(c1_phone_type, created_phone_data['type'])

        # assert role relation
        self.assertIsNotNone(role_relation_id, 'Role relation shouldn\'t be none')

        # Update mutation
        c1_first_name = "Anne"
        c1_last_name  = "Doe"
        c1_email = "adoe@pypi.org"
        c1_phone = "+34600000789"

        c3_email = "adoe@myemail.org"
        c3_email_type = "personal"
        c3_phone = "+34600111222"
        c3_phone_type = "personal"

        role_handle_id = Role.objects.all().last().handle_id

        query = '''
        mutation{{
          composite_contact(input:{{
            update_input:{{
              handle_id: {c1_handle_id}
              first_name: "{c1_first_name}"
              last_name: "{c1_last_name}"
              contact_type: "{c1_contact_type}"
            }}
            create_subinputs:[{{
              name: "{c3_email}"
              type: "{c3_email_type}"
            }}]
            update_subinputs:[{{
              handle_id: {c1_email_id}
              name: "{c1_email}"
              type: "{c1_email_type}"
            }}]
            delete_subinputs:[{{
              handle_id: {c1_email_id2}
            }}]
            create_phones:[{{
              name: "{c3_phone}"
              type: "{c3_phone_type}"
            }}]
            update_phones:[{{
              handle_id: {c1_phone_id}
              name: "{c1_phone}"
              type: "{c1_phone_type}"
            }}]
            link_rolerelations:[{{
              role_handle_id: {role_handle_id}
              organization_handle_id: {organization_id}
              relation_id: {role_relation_id}
            }}]
            delete_phones:[{{
              handle_id: {c1_phone_id2}
            }}]
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              contact{{
                handle_id
                first_name
                last_name
                contact_type
                emails{{
                  handle_id
                  name
                  type
                }}
                phones{{
                  handle_id
                  name
                  type
                }}
                roles{{
                  relation_id
                  start{{
                    handle_id
                    first_name
                  }}
                  end{{
                    handle_id
                    name
                  }}
                }}
              }}
            }}
            subcreated{{
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
            subupdated{{
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
            phones_created{{
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
            phones_updated{{
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
            rolerelations{{
              errors{{
                field
                messages
              }}
              rolerelation{{
                relation_id
                type
                start{{
                  handle_id
                  first_name
                  last_name
                }}
                end{{
                  handle_id
                  name
                }}
              }}
            }}
          }}
        }}
        '''.format(c1_handle_id=c1_handle_id, c1_first_name=c1_first_name,
                    c1_last_name=c1_last_name, c1_contact_type=c1_contact_type,
                    c3_email=c3_email, c3_email_type=c3_email_type,
                    c1_email_id=c1_email_id, c1_email=c1_email,
                    c1_email_type=c1_email_type, c1_email_id2=c1_email_id2,
                    c3_phone=c3_phone, c3_phone_type=c3_phone_type,
                    c1_phone_id=c1_phone_id, c1_phone=c1_phone,
                    c1_phone_type=c1_phone_type, role_handle_id=role_handle_id,
                    organization_id=organization_id,
                    role_relation_id=role_relation_id, c1_phone_id2=c1_phone_id2)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = result.data['composite_contact']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        for subcreated in result.data['composite_contact']['subcreated']:
            assert not subcreated['errors']

        for subupdated in result.data['composite_contact']['subupdated']:
            assert not subupdated['errors']

        for subcreated in result.data['composite_contact']['phones_created']:
            assert not subcreated['errors']

        for subupdated in result.data['composite_contact']['phones_updated']:
            assert not subupdated['errors']

        for subcreated in result.data['composite_contact']['rolerelations']:
            assert not subcreated['errors']

        # get the ids
        result_data = result.data['composite_contact']
        c1_email_id3 = result_data['subcreated'][0]['email']['handle_id']
        c1_phone_id3 = result_data['phones_created'][0]['phone']['handle_id']
        role_relation_id2 = result_data['rolerelations'][0]['rolerelation']['relation_id']

        # check the integrity of the data
        updated_data = result_data['updated']['contact']

        # check contact
        assert updated_data['first_name'] == c1_first_name, \
            "1st contact's first name doesn't match \n{} != {}"\
                .format(updated_data['first_name'], c1_first_name)
        assert updated_data['last_name'] == c1_last_name, \
            "1st contact's last name doesn't match \n{} != {}"\
                .format(updated_data['last_name'], c1_last_name)

        # get emails and check them
        email1_node = None
        email3_node = None

        for email_node in updated_data['emails']:
            if email_node['handle_id'] == c1_email_id:
                email1_node = email_node
            elif email_node['handle_id'] == c1_email_id3:
                email3_node = email_node

        self.assertIsNotNone(email1_node)

        assert c1_email_id == email1_node['handle_id'], \
            "Contact's email handle_id doesn't match \n{} != {}"\
                .format(c1_email_id, email1_node['handle_id'])
        assert c1_email == email1_node['name'], \
            "Contact's email doesn't match \n{} != {}"\
                .format(c1_email, email1_node['name'])
        assert c1_email_type == email1_node['type'], \
            "Contact's email type doesn't match \n{} != {}"\
                .format(c1_email_type, email1_node['type'])

        self.assertIsNotNone(email3_node)

        assert c1_email_id3 == email3_node['handle_id'], \
            "Contact's email handle_id doesn't match \n{} != {}"\
                .format(c1_phone_id3, email3_node['handle_id'])
        assert c3_email == email3_node['name'], \
            "Contact's email doesn't match \n{} != {}"\
                .format(c3_email, email3_node['name'])
        assert c3_email_type == email3_node['type'], \
            "Contact's email type doesn't match \n{} != {}"\
                .format(c3_email_type, email3_node['type'])


        # get phones and check them
        phone1_node = None
        phone3_node = None

        for phone_node in updated_data['phones']:
            if phone_node['handle_id'] == c1_phone_id:
                phone1_node = phone_node
            elif phone_node['handle_id'] == c1_phone_id3:
                phone3_node = phone_node

        self.assertIsNotNone(phone1_node)

        assert c1_phone_id == phone1_node['handle_id'], \
            "Contact's phone handle_id doesn't match \n{} != {}"\
                .format(c1_phone_id, phone1_node['handle_id'])
        assert c1_phone == phone1_node['name'], \
            "Contact's phone doesn't match \n{} != {}"\
                .format(c1_phone, phone1_node['name'])
        assert c1_phone_type == phone1_node['type'], \
            "Contact's phone type doesn't match \n{} != {}"\
                .format(c1_phone_type, phone1_node['type'])

        self.assertIsNotNone(phone3_node)

        assert c1_phone_id3 == phone3_node['handle_id'], \
            "Contact's phone handle_id doesn't match \n{} != {}"\
                .format(c1_phone_id, phone3_node['handle_id'])
        assert c3_phone == phone3_node['name'], \
            "Contact's phone doesn't match \n{} != {}"\
                .format(c3_phone, phone3_node['name'])
        assert c3_phone_type == phone3_node['type'], \
            "Contact's phone type doesn't match \n{} != {}"\
                .format(c3_phone_type, phone3_node['type'])

        # check rolerelation
        assert len(result_data['rolerelations']) == 1, \
            'This contact should only have one role'
        rolerelation = result_data['rolerelations'][0]['rolerelation']

        # check number of roles
        roles_data = result_data['updated']['contact']['roles']
        assert len(roles_data) == 1, \
            'This contact should only have one role'

        assert c1_handle_id == rolerelation['start']['handle_id'], \
            "Contact's handle_id doesn't match with the one present in the relation \n\
                {} != {}".format(c1_handle_id , rolerelation['start']['handle_id'],)
        assert int(organization_id) == int(rolerelation['end']['handle_id']), \
            "Organization's handle_id doesn't match with the one present in the relation\n\
                {} != {}".format(organization_id , rolerelation['end']['handle_id'],)

        # check for deleted email and phone
        c1_email_id2 = int(c1_email_id2)
        assert not NodeHandle.objects.filter(handle_id=c1_email_id2).exists(), \
            "This email node should had been deleted"

        c1_phone_id2 = int(c1_phone_id2)
        assert not NodeHandle.objects.filter(handle_id=c1_phone_id2).exists(), \
            "This phone node should had been deleted"


class MultipleMutationTest(Neo4jGraphQLTest):
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
            result.data['contacts']['edges'][0]['node']['member_of_groups'][0]['handle_id'] == group_id, \
            pformat(result.data, indent=1)
        assert \
            result.data['contacts']['edges'][1]['node']['member_of_groups'][0]['handle_id'] == group_id, \
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
