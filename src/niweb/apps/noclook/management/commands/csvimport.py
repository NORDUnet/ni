# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import User, NodeType, NodeHandle, Role, NODE_META_TYPE_CHOICES
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
        parser.add_argument('-d', "--delimiter", nargs='?', default=';',
                            help='Delimiter to use use. Default ";".')

    def handle(self, *args, **options):
        if options['fixroles']:
            self.fix_roles()
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
                    if key not in ['node_type', 'contact_role', 'name', 'account_name'] and node[key]:
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

                    # add role relatioship
                    role_name = node['contact_role']
                    role = Role.objects.get_or_create(name = role_name)[0]

                    nc.models.RoleRelationship.link_contact_organization(
                        new_contact.handle_id,
                        new_org.handle_id,
                        role.handle_id,
                        role_name
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
                    role.handle_id,
                    role_name
                )

            csv_secroles.close()

    def fix_roles(self):
        '''
        This method is provided to update an existing setup into the new
        role database representation in both databases
        '''
        # get all unique role string in all Works_for relation in neo4j db
        role_names = nc.models.RoleRelationship.get_all_roles()

        # create a role for each of them
        for role_name in role_names:
            if Role.objects.filter(name=role_name):
                role = Role.objects.filter(name=role_name).first()
            elif role_name != '':
                role = Role(name=role_name)
                role.save()

            # update the relation in neo4j using the relation_id to add the handle_id
            q = """
                MATCH (c:Contact)-[r:Works_for]->(o:Organization)
                WHERE r.name = "{role_name}"
                SET r.handle_id = {handle_id}
                RETURN r
                """.format(role_name=role_name, handle_id=role.handle_id)

            ret = nc.core.query_to_list(nc.graphdb.manager, q)

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
