# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook import helpers
from apps.noclook.models import User, NodeType, NodeHandle, Role, Dropdown, NODE_META_TYPE_CHOICES, DEFAULT_ROLE_KEY
from apps.nerds.lib.consumer_util import get_user
from django.core.management.base import BaseCommand, CommandError
from pprint import pprint
from time import sleep

import argparse
import norduniclient as nc
import logging
import traceback
import sys

logger = logging.getLogger('noclook.management.csvimport')

class Command(BaseCommand):
    help = 'Imports csv files from Salesforce'
    new_types = ['Organization', 'Procedure', 'Contact', 'Group', 'Role']

    def add_arguments(self, parser):
        parser.add_argument("-o", "--organizations", help="organizations CSV file",
                    type=argparse.FileType('r'))
        parser.add_argument("-c", "--contacts", help="contacts CSV file",
                    type=argparse.FileType('r'))
        parser.add_argument("-s", "--secroles", help="security roles CSV file",
                    type=argparse.FileType('r'))
        parser.add_argument("-f", "--fixroles",
                    action='store_true', help="regenerate roles in intermediate setup")
        parser.add_argument("-m", "--emailphones",
                    action='store_true', help="regenerate emails and phones to separate models")
        parser.add_argument("-a", "--addressfix",
                    action='store_true', help="regenerate organizations' address to the new SRI")
        parser.add_argument("-w", "--movewebsite",
                    action='store_true', help="move organizations' website back from address")
        parser.add_argument("-r", "--reorgprops",
                    action='store_true', help="rename organization properties")
        parser.add_argument('-d', "--delimiter", nargs='?', default=';',
                            help='Delimiter to use use. Default ";".')

    def handle(self, *args, **options):
        # check if the fixroles option has been called, do it and exit
        if options['fixroles']:
            self.fix_roles()
            return

        # check if the emailphones option has been called, do it and exit
        if options['emailphones']:
            self.fix_emails_phones()
            return

        # check if the addressfix option has been called, do it and exit
        if options['addressfix']:
            self.fix_organizations_address()
            return

        # check if the addressfix option has been called, do it and exit
        if options['movewebsite']:
            self.fix_website_field()
            return

        # check if the addressfix option has been called, do it and exit
        if options['reorgprops']:
            self.fix_organizations_fields()
            return

        relation_meta_type = 'Relation'
        logical_meta_type = 'Logical'

        self.delimiter = ';'
        if options['delimiter']:
            self.delimiter = options['delimiter']

        ## (We'll use handle_id on to get the node on cql code)
        # check if new types exists
        if options['verbosity'] > 0:
            self.stdout.write('Checking if the types are already in the db')

        for type in self.new_types:
            dbtype = NodeType.objects.filter(type=type)

            if not dbtype:
                dbtype = NodeType(
                    type=type,
                    slug=type.lower(),
                )
                dbtype.save()
            else:
                dbtype = dbtype.first()

        total_lines = 0

        csv_organizations = None
        csv_contacts = None
        csv_secroles = None
        self.user = get_user()

        # IMPORT ORGANIZATIONS
        if options['organizations']:
            # py: count lines
            csv_organizations = options['organizations']
            org_lines = self.count_lines(csv_organizations)

            if options['verbosity'] > 0:
                self.stdout.write('Importing {} Organizations from file "{}"'\
                    .format(org_lines, csv_organizations.name))

            total_lines = total_lines + org_lines

        # IMPORT CONTACTS AND ROLES
        if options['contacts']:
            # py: count lines
            csv_contacts = options['contacts']
            con_lines = self.count_lines(csv_contacts)

            if options['verbosity'] > 0:
                self.stdout.write('Importing {} Contacts from file "{}"'\
                    .format(con_lines, csv_contacts.name))

            total_lines = total_lines + con_lines

        # IMPORT SECURITY ROLES
        if options['secroles']:
            # py: count lines
            csv_secroles = options['secroles']
            srl_lines = self.count_lines(csv_secroles)

            if options['verbosity'] > 0:
                self.stdout.write('Importing {} Security Roles from file "{}"'\
                    .format(srl_lines, csv_secroles.name))

            total_lines = total_lines + srl_lines

        imported_lines = 0
        # print progress bar
        if options['verbosity'] > 0:
            self.printProgressBar(imported_lines, total_lines)

        # process organizations
        if options['organizations']:
            # contact
            node_type = NodeType.objects.filter(type=self.new_types[0]).first()
            csv_organizations = options['organizations']
            node_list = self.read_csv(csv_organizations, delim=self.delimiter)

            for node in node_list:
                account_name = node['account_name']

                # dj: organization exist?: create or get (using just the name)
                new_organization = NodeHandle.objects.get_or_create(
                        node_name = account_name,
                        node_type = node_type,
                        node_meta_type = relation_meta_type,
                        creator = self.user,
                        modifier = self.user,
                    )[0]

            	# n4: add attributes
                graph_node = new_organization.get_node()

                for key in node.keys():
                    if key not in ['account_name', 'parent_account'] and node[key]:
                        graph_node.add_property(key, node[key])

                	# dj: if parent organization: create or get (using just the name)
                    if key == 'parent_account' and node['parent_account']:
                        parent_org_name = node['parent_account']

                        parent_organization = NodeHandle.objects.get_or_create(
                                node_name = parent_org_name,
                                node_type = node_type,
                                node_meta_type = relation_meta_type,
                                creator = self.user,
                                modifier = self.user,
                            )[0]

                        parent_node = parent_organization.get_node()

            	        # n4: add relation between org and parent_org
                        graph_node.set_parent(parent_organization.handle_id)

                # Print iterations progress
                if options['verbosity'] > 0:
                    imported_lines = imported_lines + 1
                    self.printProgressBar(imported_lines, total_lines)

            csv_organizations.close()

        # process contacts
        if options['contacts']:
            node_type = NodeType.objects.filter(type=self.new_types[2]).first() # contact
            node_list = self.read_csv(csv_contacts, delim=self.delimiter)

            for node in node_list:
                full_name = '{} {}'.format(
                                node['first_name'],
                                node['last_name']
                            )

                # dj: contact exists?: create or get
                new_contact = NodeHandle.objects.get_or_create(
                        node_name = full_name,
                        node_type = node_type,
                        node_meta_type = relation_meta_type,
                        creator = self.user,
                        modifier = self.user,
                    )[0]

            	# n4: add attributes
                graph_node = new_contact.get_node()

                for key in node.keys():
                    if key not in ['node_type', 'contact_role', 'name', 'account_name', 'salutation'] and node[key]:
                        graph_node.add_property(key, node[key])

            	# dj: organization exist?: create or get
                organization_name = node.get('account_name', None)

                if organization_name:
                    org_type = NodeType.objects.filter(type=self.new_types[0]).first() # organization

                    new_org = NodeHandle.objects.get_or_create(
                            node_name = organization_name,
                            node_type = org_type,
                            node_meta_type = relation_meta_type,
                            creator = self.user,
                            modifier = self.user,
                        )[0]

                    # add role relatioship, use employee role if empty
                    role_name = node['contact_role']

                    if role_name:
                        role = Role.objects.get_or_create(name = role_name)[0]
                    else:
                        role = Role.objects.get(slug=DEFAULT_ROLE_KEY)

                    nc.models.RoleRelationship.link_contact_organization(
                        new_contact.handle_id,
                        new_org.handle_id,
                        role.name
                    )


                # Print iterations progress
                if options['verbosity'] > 0:
                    imported_lines = imported_lines + 1
                    self.printProgressBar(imported_lines, total_lines)

            csv_contacts.close()

        # process security roles
        if options['secroles']:
            orga_type = NodeType.objects.filter(type=self.new_types[0]).first() # organization
            cont_type = NodeType.objects.filter(type=self.new_types[2]).first() # contact
            role_type = NodeType.objects.filter(type=self.new_types[4]).first() # role
            node_list = self.read_csv(csv_secroles, delim=self.delimiter)

            for node in node_list:
                # create or get nodes
                organization = NodeHandle.objects.get_or_create(
                        node_name = node['organisation'],
                        node_type = orga_type,
                        node_meta_type = relation_meta_type,
                        creator = self.user,
                        modifier = self.user,
                    )[0]

                contact = NodeHandle.objects.get_or_create(
                        node_name = node['contact'],
                        node_type = cont_type,
                        node_meta_type = relation_meta_type,
                        creator = self.user,
                        modifier = self.user,
                    )[0]

                role_name = node['role']
                role = Role.objects.get_or_create(name = role_name)[0]

                nc.models.RoleRelationship.link_contact_organization(
                    contact.handle_id,
                    organization.handle_id,
                    role.name
                )

            csv_secroles.close()

    def fix_roles(self):
        '''
        This method is provided to update an existing setup into the new
        role database representation in both databases. It runs over the
        neo4j db and creates the existent roles into the relational db
        '''
        # get all unique role string in all Works_for relation in neo4j db
        role_names = nc.models.RoleRelationship.get_all_role_names()

        # create a role for each of them
        for role_name in role_names:
            if Role.objects.filter(name=role_name):
                role = Role.objects.filter(name=role_name).first()
            elif role_name != '':
                role = Role(name=role_name)
                role.save()

    def fix_emails_phones(self):
        self.user = get_user()

        work_type_str = 'work'
        personal_type_str = 'personal'
        logical_meta_type = 'Logical'

        old_email_fields = { 'email': work_type_str,  'other_email': personal_type_str }
        old_phone_fields = { 'phone': work_type_str,  'mobile': personal_type_str }

        # check that the options are available
        phone_type_val = Dropdown.objects.get(name="phone_type").as_values(False)
        email_type_val = Dropdown.objects.get(name="email_type").as_values(False)

        if not ((work_type_str in phone_type_val) and\
            (personal_type_str in phone_type_val) and\
            (personal_type_str in email_type_val) and\
            (personal_type_str in email_type_val)):
            raise Exception('Work/Personal values are not available for the \
                                Email/phone dropdown types')

        contact_type = NodeType.objects.get_or_create(type='Contact', slug='contact')[0] # contact
        email_type = NodeType.objects.get_or_create(type='Email', slug='email', hidden=True)[0] # contact
        phone_type = NodeType.objects.get_or_create(type='Phone', slug='phone', hidden=True)[0] # contact
        all_contacts = NodeHandle.objects.filter(node_type=contact_type)

        for contact in all_contacts:
            contact_node = contact.get_node()

            for old_phone_field, assigned_type in old_phone_fields.items():
                # phones
                if old_phone_field in contact_node.data:
                    old_phone_value = contact_node.data.get(old_phone_field)
                    new_phone = NodeHandle.objects.get_or_create(
                        node_name=old_phone_value,
                        node_type=phone_type,
                        node_meta_type=logical_meta_type,
                        creator=self.user,
                        modifier=self.user,
                    )[0]
                    contact_node.add_phone(new_phone.handle_id)
                    contact_node.remove_property(old_phone_field)
                    new_phone.get_node().add_property('type', assigned_type)

            for old_email_field, assigned_type in old_email_fields.items():
                # emails
                if old_email_field in contact_node.data:
                    old_email_value = contact_node.data.get(old_email_field)
                    new_email = NodeHandle.objects.get_or_create(
                        node_name=old_email_value,
                        node_type=email_type,
                        node_meta_type=logical_meta_type,
                        creator=self.user,
                        modifier=self.user,
                    )[0]
                    contact_node.add_email(new_email.handle_id)
                    contact_node.remove_property(old_email_field)
                    new_email.get_node().add_property('type', assigned_type)

    def fix_organizations_address(self):
        self.user = get_user()
        address_type = NodeType.objects.get_or_create(type='Address', slug='address', hidden=True)[0] # address
        organization_type = NodeType.objects.get_or_create(type='Organization', slug='organization')[0] # organization
        all_organizations = NodeHandle.objects.filter(node_type=organization_type)
        logical_meta_type = 'Logical'

        phone_field = 'phone'

        for organization in all_organizations:
            organization_node = organization.get_node()
            address_name = 'Address: {}'.format(organization.node_name)

            old_phone = organization_node.data.get(phone_field, None)

            if old_phone:
                # create an Address and asociate it to the Organization
                new_address = NodeHandle.objects.get_or_create(
                    node_name=address_name,
                    node_type=address_type,
                    node_meta_type=logical_meta_type,
                    creator=self.user,
                    modifier=self.user,
                )[0]

                new_address.get_node().add_property(phone_field, old_phone)
                organization_node.remove_property(phone_field)

                organization_node.add_address(new_address.handle_id)

    def fix_website_field(self):
        self.user = get_user()
        address_type = NodeType.objects.get_or_create(type='Address', slug='address', hidden=True)[0] # address
        organization_type = NodeType.objects.get_or_create(type='Organization', slug='organization')[0] # organization
        all_organizations = NodeHandle.objects.filter(node_type=organization_type)

        website_field = 'website'

        for organization in all_organizations:
            orgnode = organization.get_node()
            relations = orgnode.get_outgoing_relations()
            address_relations = relations.get('Has_address', None)
            if address_relations:
                for rel in address_relations:
                    address_end = rel['relationship'].end_node

                    if website_field in address_end._properties:
                        website_str = address_end._properties[website_field]
                        handle_id = address_end._properties['handle_id']
                        address_node = NodeHandle.objects.get(handle_id=handle_id).get_node()

                        # remove if it already exists
                        orgnode.remove_property(website_field)
                        orgnode.add_property(website_field, website_str)

                        # remove value in address_node
                        address_node.remove_property(website_field)

    def fix_organizations_fields(self):
        self.user = get_user()
        organization_type = NodeType.objects.get_or_create(type='Organization', slug='organization')[0] # organization
        all_organizations = NodeHandle.objects.filter(node_type=organization_type)

        old_field1 = 'customer_id'
        new_field1 = 'organization_id'

        for organization in all_organizations:
            orgnode = organization.get_node()
            org_id_val = orgnode.data.get(old_field1, None)
            if org_id_val:
                orgnode.remove_property(old_field1)
                orgnode.add_property(new_field1, org_id_val)

    def count_lines(self, file):
        '''
        Counts lines in a file
        '''
        num_lines = 0
        try:
            num_lines = sum(1 for line in file)
            logger.warn(num_lines)
            num_lines = num_lines - 1 # remove header

            file.seek(0) # reset to start line
        except IOError as e:
            self.stderr.write("I/O error({0}): {1}".format(e.errno, e.strerror))
        except: #handle other exceptions such as attribute errors
            self.stderr.write("Unexpected error:\n" + traceback.format_exc())

        return num_lines

    def normalize_whitespace(self, text):
        '''
        Remove redundant whitespace from a string.
        '''
        text = text.replace('"', '').replace("'", '')
        return ' '.join(text.split())

    def read_csv(self, f, delim=';', empty_keys=True):
        '''
        Read csv method (from csv_producer)
        '''
        node_list = []
        key_list = self.normalize_whitespace(f.readline()).split(delim)
        line = self.normalize_whitespace(f.readline())
        while line:
            value_list = line.split(delim)
            tmp = {}
            for i in range(0, len(key_list)):
                key = self.normalize_whitespace(key_list[i].replace(' ','_').lower())
                value = self.normalize_whitespace(value_list[i])
                if value or empty_keys:
                    tmp[key] = value
            node_list.append(tmp)
            line = self.normalize_whitespace(f.readline())
        return node_list

    def printProgressBar (self, iteration, total, prefix = 'Progress', suffix = 'Complete', decimals = 1, length = 100, fill = '█'):
        """
        Call in a loop to create terminal progress bar
        (from https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console)
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        self.stdout.write('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), ending = '\r')
        # Print New Line on Complete
        if iteration == total:
            self.stdout.write('')
