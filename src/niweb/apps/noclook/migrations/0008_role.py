# -*- coding: utf-8 -*-
# Generated by Django 1.11.21 on 2019-07-17 11:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('noclook', '0007_auto_20190410_1341'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('handle_id', models.AutoField(primary_key=True, serialize=False)),
                ('node_name', models.CharField(max_length=200)),
                ('description', models.TextField()),
            ],
        ),
    ]