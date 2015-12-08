# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.core.management import call_command

from django.db import models, migrations

def load_host_user_map(apps, schema_editor):
    call_command('loaddata', 'initial_host_user_map.json')


class Migration(migrations.Migration):
    dependencies = [
        ('nerds', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_host_user_map),
    ]
