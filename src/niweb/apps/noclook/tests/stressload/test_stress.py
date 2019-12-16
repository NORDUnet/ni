# -*- coding: utf-8 -*-

__author__ = 'ffuentes'

from abc import ABC, abstractmethod
from django.core.management import call_command
from niweb.schema import schema

from .data_generator import FakeDataGenerator
from ..management.fileutils import write_string_to_disk
from ..neo4j_base import NeoTestCase

import logging
import timeit
import unittest
import os
import sys

#logging.basicConfig( stream=sys.stderr )
logger = logging.getLogger('StressTest')
skip_reason = "This test should be run explicitly.:\
                STRESS_TEST=1 ./manage.py test apps/noclook/tests/stressload/"

class AbstractStressTest(ABC):
    import_cmd = 'csvimport'
    org_csv_head = '"organization_number";"account_name";"description";"phone";"website";"organization_id";"type";"parent_account"'
    con_csv_head = '"salutation";"first_name";"last_name";"title";"contact_role";"contact_type";"mailing_street";"mailing_city";"mailing_zip";"mailing_state";"mailing_country";"phone";"mobile";"fax";"email";"other_email";"PGP_fingerprint";"account_name"'

    setup_code = """
import apps.noclook.vakt.utils as sriutils
from apps.noclook.models import Group, GroupContextAuthzAction
from django.contrib.auth.models import User
from niweb.schema import schema

class TestContext():
    def __init__(self, user, *ignore):
        self.user = user

user = User.objects.filter(username='test user')

if not user:
    user = User.objects.get_or_create(username='test user', password='test')[0]
else:
    user = user.first()

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

    @unittest.skipUnless(os.environ.get('STRESS_TEST'), skip_reason)
    def test_organization_list(self):
        query = '''
        {
          ...OrganizationList_organizations_1tT5Hu
          ...OrganizationList_organization_types
        }

        fragment OrganizationList_organization_types on Query {
          getChoicesForDropdown(name: "organization_types") {
            name
            value
            id
          }
        }

        fragment OrganizationList_organizations_1tT5Hu on Query {
          organizations(filter: {}, orderBy: handle_id_DESC) {
            edges {
              node {
                handle_id
                ...OrganizationRow_organization
                id
                __typename
              }
              cursor
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }

        fragment OrganizationRow_organization on Organization {
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
          parent_organization {
            organization_id
            id
          }
          incoming {
            name
            relation {
              type
              start {
                handle_id
                node_name
                id
              }
              id
            }
          }
        }
        '''

        setup_code = self.setup_code.format(query_value=query)

        mark1 = timeit.Timer("""schema.execute(query, context=context)""", \
            setup=setup_code).timeit(1)

        test_result = "Full organization list resolution for {} took {} ms".format(self, mark1)

    @unittest.skipUnless(os.environ.get('STRESS_TEST'), skip_reason)
    def test_contact_list(self):
        query = '''
        query SearchContactsAllQuery{
          ...ContactList_contacts_1tT5Hu
          ...ContactList_organization_types
          ...ContactList_roles_default
        }

        fragment ContactList_contacts_1tT5Hu on Query {
          contacts(filter: {}, orderBy: handle_id_DESC) {
            edges {
              node {
                handle_id
                ...ContactRow_contact
                id
                __typename
              }
              cursor
            }
            pageInfo {
              endCursor
              hasNextPage
              hasPreviousPage
              startCursor
            }
          }
        }

        fragment ContactList_organization_types on Query {
          getChoicesForDropdown(name: "organization_types") {
            name
            value
            id
          }
        }

        fragment ContactList_roles_default on Query {
          getRolesFromRoleGroup {
            handle_id
            name
          }
        }

        fragment ContactRow_contact on Contact {
          handle_id
          first_name
          last_name
          contact_type
          modified
          roles {
            name
            end {
              name
              id
            }
          }
        }
        '''

        setup_code = self.setup_code.format(query_value=query)

        mark1 = timeit.Timer("""schema.execute(query, context=context)""", \
            setup=setup_code).timeit(1)

        test_result = "Full contact list resolution for {} took {} ms".format(self, mark1)


class LowStressTest(NeoTestCase, AbstractStressTest):
    contact_num = 10
    organization_num = 10

    def setUp(self):
        super(LowStressTest, self).setUp()
        self.load_nodes()


class MidStressTest(NeoTestCase, AbstractStressTest):
    contact_num = 50
    organization_num = 50

    def setUp(self):
        super(MidStressTest, self).setUp()
        self.load_nodes()
