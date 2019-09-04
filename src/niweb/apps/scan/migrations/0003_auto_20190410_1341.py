# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-04-10 13:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scan', '0002_auto_20190121_0856'),
    ]

    operations = [
        migrations.AlterField(
            model_name='queueitem',
            name='status',
            field=models.CharField(choices=[('QUEUED', 'Queued'), ('PROCESSING', 'Processing'), ('DONE', 'Done'), ('FAILED', 'Failed')], default='QUEUED', max_length=255),
        ),
        migrations.AlterField(
            model_name='queueitem',
            name='type',
            field=models.CharField(choices=[('Host', 'Host')], max_length=255),
        ),
    ]
