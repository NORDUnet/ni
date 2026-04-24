# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('noclook', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='nodetype',
            name='hidden',
            field=models.BooleanField(default=False, help_text=b'Hide from menus'),
        ),
    ]
