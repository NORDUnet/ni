# -*- coding: utf-8 -*-
# Generated by Django 1.11.21 on 2019-07-17 12:40
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('noclook', '0008_role'),
    ]

    operations = [
        migrations.RenameField(
            model_name='role',
            old_name='node_name',
            new_name='name',
        ),
    ]