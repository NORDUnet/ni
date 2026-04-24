# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

class Migration(migrations.Migration):

    dependencies = [
        ('noclook', '0002_nodetype_hidden'),
    ]

    operations = [
        migrations.CreateModel(
            name='HostUserMap',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('domain', models.CharField(max_length=255, unique=True)),
                ('host_user', models.CharField(max_length=255)),
            ],
        ),
    ]
