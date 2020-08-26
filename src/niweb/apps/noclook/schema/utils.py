# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import Dropdown, Choice

import csv
import os

def add_sunet_dropdowns():
    ret = False

    if not Dropdown.objects.filter(name="tele2_cable_contracts").exists():
        dir_path = os.path.dirname(os.path.realpath(__file__))

        with open('{}/../../../../scripts/updates_and_fixes/dropdown_defaults/sunet_dropdowns.csv'.format(dir_path), 'r') as csv_file:
            for row in csv.DictReader(csv_file):
                dropdown, created = Dropdown.objects.get_or_create(name=row['dropdown'])
                value = row['value']
                name = row['name'] or value

                if value:
                    Choice.objects.get_or_create(dropdown=dropdown,
                                                 value=value,
                                                 name=name)

                ret = True

    return ret
