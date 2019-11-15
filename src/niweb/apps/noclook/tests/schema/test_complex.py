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
                    c2_mail=c2_mail, email_type2=email_type)

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
            "1st contact's group name doesn't match \n{} != {}"\
                .format(subcreated_data[1]['contact']['member_of_groups'][0]['name'], group_name)

class OrganizationComplexTest(Neo4jGraphQLTest):
    def test_composite_organization(self):
        org_name = "PyPI"
        org_type = "partner"
        org_id = "AABA"
        parent_org_id = self.organization1.handle_id
        org_web = "pypi.org"
        org_num = "55446"

        c1_first_name = "Janet"
        c1_last_name  = "Doe"
        c1_contact_type = "person"
        c1_email = "jdoe@pypi.org"
        c1_email_type = "work"
        c1_phone = "+34600123456"
        c1_phone_type = "work"

        org_addr_name = "Main"
        org_addr_st = "Fake St. 123"
        org_addr_pcode = "21500"
        org_addr_parea = "Huelva"

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
                contact_type: "{c1_contact_type}"
                email: "{c1_email}"
                email_type: "{c1_email_type}"
                phone:"{c1_phone}"
                phone_type: "{c1_phone_type}"
              }}
            ]
            create_address:[
              {{
                name: "{org_addr_name}"
                street: "{org_addr_st}"
                postal_code: "{org_addr_pcode}"
                postal_area: "{org_addr_parea}"
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
                    c1_contact_type=c1_contact_type, c1_email=c1_email,
                    c1_email_type=c1_email_type, c1_phone=c1_phone,
                    c1_phone_type=c1_phone_type, org_addr_name=org_addr_name,
                    org_addr_st=org_addr_st, org_addr_pcode=org_addr_pcode,
                    org_addr_parea=org_addr_parea)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_organization']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        for subcreated in result.data['composite_organization']['subcreated']:
            assert not subcreated['errors']

        # get the ids
        result_data = result.data['composite_organization']
        organization_handle_id = result_data['created']['organization']['handle_id']
        c1_handle_id = result_data['subcreated'][0]['contact']['handle_id']
        c1_email_id = result_data['subcreated'][0]['contact']['emails'][0]['handle_id']
        c1_phone_id = result_data['subcreated'][0]['contact']['phones'][0]['handle_id']

        # check the integrity of the data
        created_data = result_data['created']['organization']

        # check group
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

        subcreated_data = result_data['subcreated']

        # contact
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
