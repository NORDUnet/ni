# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import User, NodeType, NodeHandle, NODE_META_TYPE_CHOICES
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
        parser.add_argument('-d', "--delimiter", nargs='?', default=';',
                            help='Delimiter to use use. Default ";".')

    def handle(self, *args, **options):
        relation_meta_type = NODE_META_TYPE_CHOICES[2][1] # relation
        logical_meta_type = NODE_META_TYPE_CHOICES[1][1] # logical

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
        self.user = User.objects.filter(username='admin').first()

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

        imported_lines = 0
        # print progress bar
        if options['verbosity'] > 0:
            self.printProgressBar(imported_lines, total_lines)

        # process organizations
        if options['organizations']:
            # contact
            node_type = NodeType.objects.filter(type=self.new_types[0]).first()
            csv_organizations = options['organizations']
            node_list = self.read_csv(csv_organizations)

            for node in node_list:
                account_name = node['account_name']

                # dj: organization exist?: create or get (using just the name)
                new_organization = self.get_or_create(
                        account_name,
                        node_type,
                        relation_meta_type
                    )

            	# n4: add attributes
                graph_node = new_organization.get_node()

                graph_node.add_property('name', account_name)
                for key in node.keys():
                    if key not in ['account_name', 'parent_account'] and node[key]:
                        graph_node.add_property(key, node[key])

                	# dj: if parent organization: create or get (using just the name)
                    if key == 'parent_account' and node['parent_account']:
                        parent_org_name = node['parent_account']

                        parent_organization = self.get_or_create(
                                parent_org_name,
                                node_type,
                                relation_meta_type
                            )

                        parent_node = parent_organization.get_node()
                        parent_node.add_property('name', parent_org_name)

            	        # n4: add relation between org and parent_org
                        graph_node.set_parent(parent_organization.pk)

                # Print iterations progress
                if options['verbosity'] > 0:
                    imported_lines = imported_lines + 1
                    self.printProgressBar(imported_lines, total_lines)

            csv_organizations.close()

        # process contacts
        if options['contacts']:
            node_type = NodeType.objects.filter(type=self.new_types[2]).first() # contact
            node_list = self.read_csv(csv_contacts)

            for node in node_list:
                full_name = '{} {}'.format(
                                node['first_name'],
                                node['last_name']
                            )

                # dj: contact exists?: create or get
                new_contact = self.get_or_create(
                        full_name,
                        node_type,
                        relation_meta_type
                    )

            	# n4: add attributes
                graph_node = new_contact.get_node()

                graph_node.add_property('name', full_name)
                for key in node.keys():
                    if key not in ['node_type', 'contact_role', 'name', 'account_name'] and node[key]:
                        graph_node.add_property(key, node[key])

            	# dj: role exist?: create or get
                role_name = node['contact_role']

                if role_name:
                    role_type = NodeType.objects.filter(type=self.new_types[4]).first() # role
                    new_role = self.get_or_create(
                            role_name,
                            role_type,
                            logical_meta_type
                        )

            	    # n4: add relation between role and contact
                    graph_node.add_role(new_role.pk)

            	# dj: organization exist?: create or get
                organization_name = node['account_name']

                if organization_name:
                    org_type = NodeType.objects.filter(type=self.new_types[0]).first() # organization

                    new_org = self.get_or_create(
                            organization_name,
                            org_type,
                            relation_meta_type
                        )

                    # n4: add relation between role and organization
                    graph_node.add_organization(new_org.pk)

                # Print iterations progress
                if options['verbosity'] > 0:
                    imported_lines = imported_lines + 1
                    self.printProgressBar(imported_lines, total_lines)

            csv_contacts.close()

    # replace all the duplicate code
    def get_or_create(self, node_name, node_type, node_meta_type):
        new_node = None

        if not node_name:
            raise Exception('Empty node_name')

        qs = NodeHandle.objects.filter(
                node_name = node_name,
                node_type = node_type
            )

        if qs:
            new_node = qs.first()
        else:
            new_node = NodeHandle(
                node_name = node_name,
                node_type = node_type,
                node_meta_type = node_meta_type,
                creator = self.user,
                modifier = self.user,
            )

            new_node.save()

        return new_node

    def count_lines(self, file):
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
