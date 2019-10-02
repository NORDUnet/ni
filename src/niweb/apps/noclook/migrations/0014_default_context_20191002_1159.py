# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2019-10-02 11:59
from __future__ import unicode_literals

from django.db import migrations

import apps.noclook.vakt.utils as sriutils


# add default community context to all nodes with these types
for_types = [
    'organization',
    'procedure',
    'contact',
    'group',
    'email',
    'phone',
]

def forwards_func(apps, schema_editor):
    Context = apps.get_model('noclook', 'Context')
    NodeType = apps.get_model('noclook', 'NodeType')
    NodeHandle = apps.get_model('noclook', 'NodeHandle')
    NodeHandleContext = apps.get_model('noclook', 'NodeHandleContext')

    default_context = sriutils.get_default_context(Context)
    types_qs = NodeType.objects.filter(slug__in=for_types)
    nodes = NodeHandle.objects.filter(node_type__in=types_qs)

    for node in nodes:
        NodeHandleContext(
            nodehandle=node,
            context=default_context
        ).save()


def backwards_func(apps, schema_editor):
    NodeHandleContext = apps.get_model('noclook', 'NodeHandleContext')
    NodeHandleContext.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('noclook', '0013_default_policies_20190927_1937'),
    ]

    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ]
