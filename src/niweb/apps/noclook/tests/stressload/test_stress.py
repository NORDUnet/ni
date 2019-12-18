# -*- coding: utf-8 -*-

__author__ = 'ffuentes'

from abc import ABC, abstractmethod
from apps.noclook.models import User, NodeType, NodeHandle, Role
from apps.noclook.helpers import set_member_of, set_works_for
from apps.nerds.lib.consumer_util import get_user
from django.core.management import call_command
from niweb.schema import schema

from .data_generator import FakeDataGenerator
from ..management.fileutils import write_string_to_disk
from ..neo4j_base import NeoTestCase

import logging
import norduniclient as nc
import random
import sys
import timeit
import os
import unittest

#logging.basicConfig( stream=sys.stderr )
logger = logging.getLogger('StressTest')
skip_reason = "This test should be run explicitly.:\
                STRESS_TEST=1 ./manage.py test apps/noclook/tests/stressload/"

class AbstractStressTest(ABC):
    import_cmd = 'csvimport'
    org_csv_head = '"organization_number";"account_name";"description";"phone";"website";"organization_id";"type";"parent_account"'
    con_csv_head = '"salutation";"first_name";"last_name";"title";"contact_role";"contact_type";"mailing_street";"mailing_city";"mailing_zip";"mailing_state";"mailing_country";"phone";"mobile";"fax";"email";"other_email";"PGP_fingerprint";"account_name"'

    log_file = 'stress_log.txt'

    setup_code = """
from apps.noclook.models import Group, GroupContextAuthzAction
from apps.nerds.lib.consumer_util import get_user
from django.contrib.auth.models import User
from niweb.schema import schema

import apps.noclook.vakt.utils as sriutils

class TestContext():
    def __init__(self, user, *ignore):
        self.user = user

user = get_user()

context = TestContext(user)

group_read  = Group.objects.get_or_create( name="Group can read the community context" )[0]
group_write = Group.objects.get_or_create( name="Group can write for the community context" )[0]
group_list = Group.objects.get_or_create( name="Group can list for the community context" )[0]

# add user to this group
group_read.user_set.add(user)
group_write.user_set.add(user)
group_list.user_set.add(user)

# get read aa
get_read_authaction  = sriutils.get_read_authaction()
get_write_authaction = sriutils.get_write_authaction()
get_list_authaction  = sriutils.get_list_authaction()

# get default context
community_ctxt = sriutils.get_default_context()

# add contexts and profiles
GroupContextAuthzAction.objects.get_or_create(
    group = group_read,
    authzprofile = get_read_authaction,
    context = community_ctxt
)[0]

GroupContextAuthzAction.objects.get_or_create(
    group = group_write,
    authzprofile = get_write_authaction,
    context = community_ctxt
)[0]

GroupContextAuthzAction.objects.get_or_create(
    group = group_list,
    authzprofile = get_list_authaction,
    context = community_ctxt
)[0]

query='''{query_value}'''
    """

    def load_nodes(self):
        generator = FakeDataGenerator()

        # create organization's file
        org_list = []

        for i in range(self.organization_num):
            organization = generator.create_fake_organization()
            organization['organization_number'] = str(i+1)
            str_value = '"{}"'.format('";"'.join(organization.values()))
            org_list.append(str_value)

        org_str = '{}\n{}'.format(self.org_csv_head, '\n'.join(org_list))

        # write string to file
        org_file = write_string_to_disk(org_str)

        # create contacts's file
        con_list = []

        for i in range(self.contact_num):
            contact = generator.create_fake_contact()
            str_value = '"{}"'.format('";"'.join(contact.values()))
            con_list.append(str_value)

        con_str = '{}\n{}'.format(self.con_csv_head, '\n'.join(con_list))

        # write string to file
        con_file = write_string_to_disk(con_str)

        # import organizations file
        call_command(
            self.import_cmd,
            organizations=org_file,
            verbosity=0,
        )

        # import contacts file
        call_command(
            self.import_cmd,
            contacts=con_file,
            verbosity=0,
        )

        # call data modifiers
        call_command(self.import_cmd, emailphones=True, verbosity=0)
        call_command(self.import_cmd, addressfix=True, verbosity=0)
        call_command(self.import_cmd, movewebsite=True, verbosity=0)
        call_command(self.import_cmd, reorgprops=True, verbosity=0)

        # create groups and add members
        group_list = []
        group_type = NodeType.objects.filter(type='Group').first()
        contact_type = NodeType.objects.filter(type='Contact').first()
        user = get_user()

        contact_ids = [ x.handle_id for x in NodeHandle.objects.filter(node_type=contact_type)]

        for i in range(self.group_num):
            group_dict = generator.create_fake_group()

            # create group
            group = NodeHandle.objects.get_or_create(
                node_name = group_dict['name'],
                node_type = group_type,
                node_meta_type = nc.META_TYPES[1],
                creator = user,
                modifier = user,
            )[0]
            group_node = group.get_node()
            group_node.add_property('description', group_dict['description'])

            # add contacts (get them randomly)
            hids = random.sample(
                contact_ids, min(len(contact_ids), self.contacts_per_group)
            )
            gcontacts = NodeHandle.objects.filter(handle_id__in=hids)

            for contact in gcontacts:
                set_member_of(user, contact.get_node(), group.handle_id)

        # add members to organizations
        organization_type = NodeType.objects.filter(type='Organization').first()
        role_ids = [x.handle_id for x in Role.objects.all()]
        for organization in NodeHandle.objects.filter(node_type=organization_type):
            hids = random.sample(
                contact_ids, min(len(contact_ids), self.contacts_per_organization)
            )
            ocontacts = NodeHandle.objects.filter(handle_id__in=hids)

            for contact in ocontacts:
                rand_role = Role.objects.get(handle_id = random.choice(role_ids))
                set_works_for(user, contact.get_node(), organization.handle_id,
                                rand_role.name)

    def empty_file(self):
        open('/app/niweb/logs/{}'.format(self.log_file), 'w').close()

    def write_to_log_file(self, to_write):
        with open('/app/niweb/logs/{}'.format(self.log_file), 'a') as f:
            f.write(to_write)

    def test_lists(self):
        organizations_query = '''
        {{
          ...OrganizationList_organizations_1tT5Hu
          ...OrganizationList_organization_types
        }}

        fragment OrganizationList_organization_types on Query {{
          getChoicesForDropdown(name: "organization_types") {{
            name
            value
            id
          }}
        }}

        fragment OrganizationList_organizations_1tT5Hu on Query {{
          organizations(filter: {filter}, orderBy: {order_by}) {{
            edges {{
              node {{
                handle_id
                ...OrganizationRow_organization
                id
                __typename
              }}
              cursor
            }}
            pageInfo {{
              hasNextPage
              endCursor
            }}
          }}
        }}

        fragment OrganizationRow_organization on Organization {{
          handle_id
          name
          type
          organization_id
          affiliation_customer
          affiliation_end_customer
          affiliation_host_user
          affiliation_partner
          affiliation_provider
          affiliation_site_owner
          parent_organization {{
            organization_id
            id
          }}
          incoming {{
            name
            relation {{
              type
              start {{
                handle_id
                node_name
                id
              }}
              id
            }}
          }}
        }}
        '''

        # order by id: native django order
        by_id_query = organizations_query.format(filter={}, order_by='handle_id_DESC')
        setup_code = self.setup_code.format(query_value=by_id_query)

        mark1 = timeit.Timer("""result = schema.execute(query, context=context); assert result.data""", \
            setup=setup_code).timeit(1)

        test_result = "Organization list resolution with default order took {} seconds\n".format(mark1)
        self.write_to_log_file(test_result)

        # order by id: native django order
        name_query = organizations_query.format(filter={}, order_by='name_DESC')
        setup_code = self.setup_code.format(query_value=name_query)
        mark2 = timeit.Timer("""result = schema.execute(query, context=context); assert result.data""", \
            setup=setup_code).timeit(1)

        test_result = "Organization list resolution with name order took {} seconds\n".format(mark2)
        self.write_to_log_file(test_result)

        contacts_query = '''
        query SearchContactsAllQuery{{
          ...ContactList_contacts_1tT5Hu
          ...ContactList_organization_types
          ...ContactList_roles_default
        }}

        fragment ContactList_contacts_1tT5Hu on Query {{
          contacts(filter: {filter}, orderBy: {order_by}) {{
            edges {{
              node {{
                handle_id
                ...ContactRow_contact
                id
                __typename
              }}
              cursor
            }}
            pageInfo {{
              endCursor
              hasNextPage
              hasPreviousPage
              startCursor
            }}
          }}
        }}

        fragment ContactList_organization_types on Query {{
          getChoicesForDropdown(name: "organization_types") {{
            name
            value
            id
          }}
        }}

        fragment ContactList_roles_default on Query {{
          getRolesFromRoleGroup {{
            handle_id
            name
          }}
        }}

        fragment ContactRow_contact on Contact {{
          handle_id
          first_name
          last_name
          contact_type
          modified
          roles {{
            name
            end {{
              name
              id
            }}
          }}
        }}
        '''

        # order by id: native django order
        by_id_query = contacts_query.format(filter={}, order_by='handle_id_DESC')
        setup_code = self.setup_code.format(query_value=by_id_query)

        mark1 = timeit.Timer("""result = schema.execute(query, context=context); assert result.data""", \
            setup=setup_code).timeit(1)

        test_result = "Contact list resolution with default order took {} seconds\n".format(mark1)
        self.write_to_log_file(test_result)

        # order by id: native django order
        name_query = contacts_query.format(filter={}, order_by='name_DESC')
        setup_code = self.setup_code.format(query_value=name_query)
        mark2 = timeit.Timer("""result = schema.execute(query, context=context); assert result.data""", \
            setup=setup_code).timeit(1)

        test_result = "Contact list resolution with name order took {} seconds\n".format(mark2)
        self.write_to_log_file(test_result)

        groups_query = '''
        query SearchGroupAllQuery{{
          ...GroupList_groups_1tT5Hu
        }}

        fragment GroupList_groups_1tT5Hu on Query {{
          groups(filter: {filter}, orderBy: {order_by}) {{
            edges {{
              node {{
                handle_id
                ...GroupRow_group
                id
                __typename
              }}
              cursor
            }}
            pageInfo {{
              hasNextPage
              endCursor
            }}
          }}
        }}

        fragment GroupRow_group on Group {{
          handle_id
          name
          description
        }}
        '''

        # order by id: native django order
        by_id_query = groups_query.format(filter={}, order_by='handle_id_DESC')
        setup_code = self.setup_code.format(query_value=by_id_query)

        mark1 = timeit.Timer("""result = schema.execute(query, context=context); assert result.data""", \
            setup=setup_code).timeit(1)

        test_result = "Group list resolution with default order took {} seconds\n".format(mark1)
        self.write_to_log_file(test_result)

        # order by id: native django order
        name_query = groups_query.format(filter={}, order_by='name_DESC')
        setup_code = self.setup_code.format(query_value=name_query)
        mark2 = timeit.Timer("""result = schema.execute(query, context=context); assert result.data""", \
            setup=setup_code).timeit(1)

        test_result = "Group list resolution with name order took {} seconds\n".format(mark2)
        self.write_to_log_file(test_result)

@unittest.skipUnless(int(os.environ.get('STRESS_TEST', '0')) >= 1, skip_reason)
class LowStressTest(NeoTestCase, AbstractStressTest):
    contact_num = 5
    organization_num = 5
    group_num = 3
    contacts_per_group = 3
    contacts_per_organization = 3

    def setUp(self):
        super(LowStressTest, self).setUp()
        NodeHandle.objects.all().delete()
        self.load_nodes()


@unittest.skipUnless(int(os.environ.get('STRESS_TEST', '0')) >= 2, skip_reason)
class MidStressTest(NeoTestCase, AbstractStressTest):
    contact_num = 50
    organization_num = 50
    group_num = 10
    contacts_per_group = 25
    contacts_per_organization = 10

    def setUp(self):
        super(MidStressTest, self).setUp()
        NodeHandle.objects.all().delete()
        self.load_nodes()


@unittest.skipUnless(int(os.environ.get('STRESS_TEST', '0')) >= 3, skip_reason)
class HighStressTest(NeoTestCase, AbstractStressTest):
    contact_num = 500
    organization_num = 500
    group_num = 100
    contacts_per_group = 100
    contacts_per_organization = 50

    def setUp(self):
        super(HighStressTest, self).setUp()
        NodeHandle.objects.all().delete()
        self.load_nodes()
