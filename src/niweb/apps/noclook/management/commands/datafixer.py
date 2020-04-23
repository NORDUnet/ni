# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook import helpers
from apps.noclook.models import User, NodeType, NodeHandle, Dropdown, Choice
from apps.nerds.lib.consumer_util import get_user
from django.core.management.base import BaseCommand, CommandError
from pprint import pprint
from time import sleep

import argparse
import norduniclient as nc
import logging
import traceback
import sys

logger = logging.getLogger('noclook.management.datafixer')

class Command(BaseCommand):
    help = 'Fix local data'

    def add_arguments(self, parser):
        parser.add_argument("-x", "--fixtestdata",
                    action='store_true',
                    help="fix the test data to avoid conflicts with the front")

    def handle(self, *args, **options):
        if options['fixtestdata']:
            self.fix_test_data()
            return

    def fix_test_data(self):
        self.user = get_user()

        organization_type = NodeType.objects.get_or_create(
            type='Organization', slug='organization')[0] # organization
        contact_type = NodeType.objects.get_or_create(
            type='Contact', slug='contact')[0] # organization

        # fix all organizations
        all_organizations = NodeHandle.objects.filter(node_type=organization_type)


        total_lines = all_organizations.count()
        current_line = 0

        org_types_drop = Dropdown.objects.get(name='organization_types')
        org_types = Choice.objects.filter(dropdown=org_types_drop)

        first_field = 'type'
        second_field = 'organization_id'
        organization_ids = {}

        # get all the possible organizations id
        for organization in all_organizations:
            orgnode = organization.get_node()

            organization_id = orgnode.data.get(second_field, None)

            if organization_id not in organization_ids:
                organization_ids[organization_id] = [organization.handle_id]
            else:
                organization_ids[organization_id].append(organization.handle_id)

        total_lines = total_lines + len(organization_ids)

        # fix all contacts
        all_contacts = NodeHandle.objects.filter(node_type=contact_type)

        con_types_drop = Dropdown.objects.get(name='contact_type')
        con_types = Choice.objects.filter(dropdown=con_types_drop)

        total_lines = total_lines + all_contacts.count()

        # fix organization type
        for organization in all_organizations:
            self.printProgressBar(current_line, total_lines)

            orgnode = organization.get_node()
            org_type = orgnode.data.get(first_field, None)

            if org_type:
                correct_type = org_types.filter(value=org_type).exists()

                if not correct_type:
                    # get the first value as default
                    selected_type = org_types.first()

                    # check if exist choice with that name
                    if org_types.filter(name__icontains=org_type).exists():
                        selected_type = org_types.filter(name__icontains=org_type).first()
                    elif org_types.filter(value__icontains=org_type).exists():
                        # if not, check if exists with that value
                        selected_type = org_types.filter(value__icontains=org_type).first()

                    orgnode.remove_property(first_field)
                    orgnode.add_property(first_field, selected_type.value)

            current_line = current_line + 1

        # fix contact type
        con_type_field = 'contact_type'
        for contact in all_contacts:
            self.printProgressBar(current_line, total_lines)

            connode = contact.get_node()
            con_type = connode.data.get(con_type_field, None)

            if con_type:
                correct_type = con_types.filter(value=con_type).exists()

                if not correct_type:
                    # get the first value as default
                    selected_type = con_types.first()

                    # check if exist choice with that name
                    if con_types.filter(name__icontains=con_type).exists():
                        selected_type = con_types.filter(name__icontains=con_type).first()
                    elif con_types.filter(value__icontains=org_type).exists():
                        # if not, check if exists with that value
                        selected_type = con_types.filter(value__icontains=con_type).first()

                    connode.remove_property(con_type_field)
                    connode.add_property(con_type_field, selected_type.value)

            current_line = current_line + 1

        for organization_id, org_handle_ids in organization_ids.items():
            self.printProgressBar(current_line, total_lines)

            # check if the array lenght is more than one
            if len(org_handle_ids) > 1:
                for org_handle_id in org_handle_ids:
                    # if it is so, iterate and check if the uppercased name of the
                    # organization is already set as organization_id
                    organization = NodeHandle.objects.get(handle_id=org_handle_id)
                    orgnode = organization.get_node()
                    possible_org_id = organization.node_name.upper()
                    count = self.checkOrgInUse(possible_org_id)

                    # if it's alredy in use, append handle_id
                    if count > 0:
                        possible_org_id = '{}_{}'.format(
                            possible_org_id, organization.handle_id
                        )

                    orgnode.remove_property(second_field)
                    orgnode.add_property(second_field, possible_org_id)

            current_line = current_line + 1

        self.printProgressBar(current_line, total_lines)

    def checkOrgInUse(self, organization_id):
        q = """
            MATCH (o:Organization) WHERE o.organization_id = '{organization_id}'
            RETURN COUNT(DISTINCT o.organization_id) AS orgs;
            """.format(organization_id=organization_id)
        res = nc.query_to_dict(nc.graphdb.manager, q)

        return res['orgs']

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
