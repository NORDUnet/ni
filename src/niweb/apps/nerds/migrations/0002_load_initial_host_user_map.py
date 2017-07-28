# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from os.path import dirname, abspath, join
import csv

from django.db import models, migrations

MIGRATION_DIR = dirname(abspath(__file__))


def add_host_user_map(apps, schema_editor):
    HostUserMap = apps.get_model('nerds', 'HostUserMap')

    with open(join(MIGRATION_DIR, 'host_user_map.csv')) as f:
        for line in csv.DictReader(f):
            if line['domain'] and line['host_user']:
                HostUserMap.objects.get_or_create(domain=line['domain'],
                                                  host_user=line['host_user'])


def remove_host_user_map(apps, schema_editor):
    HostUserMap = apps.get_model('nerds', 'HostUserMap')

    with open(join(MIGRATION_DIR, 'host_user_map.csv')) as f:
        unique_domains = set([l['domain'] for l in csv.DictReader(f)])
        for domain in unique_domains:
            HostUserMap.objects.filter(domain=domain).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('nerds', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_host_user_map, remove_host_user_map),
    ]
