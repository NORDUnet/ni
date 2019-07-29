# -*- coding: utf-8 -*-
# Generated by Django 1.11.21 on 2019-07-25 11:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('noclook', '0012_role_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='role',
            name='name',
            field=models.CharField(max_length=200, unique=True),
        ),
        migrations.AlterField(
            model_name='role',
            name='slug',
            field=models.CharField(max_length=200, unique=True),
        ),
    ]