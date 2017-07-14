# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from os.path import dirname, abspath, join
import csv
from sets import Set

BASE_DIR = dirname(abspath(__file__))


def add_default_dropdowns(apps, schema_editor):
    Dropdown = apps.get_model('noclook', 'Dropdown')
    Choice = apps.get_model('noclook', 'Choice')

    with open(join(BASE_DIR, 'common_dropdowns.csv')) as f:
        for line in csv.DictReader(f):
            dropdown, created = Dropdown.objects.get_or_create(name=line['dropdown'])
            value = line['value']
            name = line['name'] or value
            if value:
                Choice.objects.get_or_create(dropdown=dropdown,
                                             value=value,
                                             name=name)


def remove_default_dropdowns(apps, schema_editor):
    Dropdown = apps.get_model('noclook', 'Dropdown')
    with open(join(BASE_DIR, 'common_dropdowns.csv')) as f:
        unique_dropdowns = Set([l['dropdown'] for l in csv.DictReader(f)])
        for dropdown in unique_dropdowns:
            Dropdown.objects.filter(name=dropdown).delete()


def migrate_optical_node_types(apps, schema_editor):
    Dropdown = apps.get_model('noclook', 'Dropdown')
    Choice = apps.get_model('noclook', 'Choice')
    ONT = apps.get_model('noclook', 'OpticalNodeType')

    dropdown, created = Dropdown.objects.get_or_create(name='optical_node_types')
    for ot in ONT.objects.all():
        Choice.objects.get_or_create(dropdown=dropdown,
                                     value=ot.name,
                                     name=ot.name)


class Migration(migrations.Migration):

    dependencies = [
        ('noclook', '0005_auto_20170612_1543'),
    ]

    operations = [
        migrations.RunPython(add_default_dropdowns, remove_default_dropdowns),
        migrations.RunPython(migrate_optical_node_types, migrations.RunPython.noop)
    ]
