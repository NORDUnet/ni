# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-01-21 08:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scan', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='queueitem',
            name='status',
            field=models.CharField(choices=[(b'QUEUED', b'Queued'), (b'PROCESSING', b'Processing'), (b'DONE', b'Done'), (b'FAILED', b'Failed')], default=b'QUEUED', max_length=255),
        ),
    ]
