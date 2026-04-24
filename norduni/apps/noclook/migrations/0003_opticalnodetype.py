# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def initial_optical_node_type(apps, schema_editor):
    OpticalNodeType = apps.get_model('noclook', 'OpticalNodeType')
    OpticalNodeType.objects.get_or_create(name="ciena6500")

class Migration(migrations.Migration):

    dependencies = [
        ('noclook', '0002_nodetype_hidden'),
    ]

    operations = [
        migrations.CreateModel(
            name='OpticalNodeType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
            ],
        ),
        migrations.RunPython(initial_optical_node_type),
    ]
