# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='NodeHandle',
            fields=[
                ('handle_id', models.AutoField(serialize=False, primary_key=True)),
                ('node_name', models.CharField(max_length=200)),
                ('node_meta_type', models.CharField(max_length=255, choices=[(b'Physical', b'Physical'), (b'Logical', b'Logical'), (b'Relation', b'Relation'), (b'Location', b'Location')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('creator', models.ForeignKey(related_name='creator', to=settings.AUTH_USER_MODEL)),
                ('modifier', models.ForeignKey(related_name='modifier', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='NodeType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(unique=True, max_length=255)),
                ('slug', models.SlugField(help_text=b'Suggested value         #automatically generated from type. Must be unique.', unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='NordunetUniqueId',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('unique_id', models.CharField(unique=True, max_length=256)),
                ('reserved', models.BooleanField(default=False)),
                ('reserve_message', models.CharField(max_length=512, null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('reserver', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='UniqueIdGenerator',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=256)),
                ('base_id', models.IntegerField(default=1)),
                ('zfill', models.BooleanField()),
                ('base_id_length', models.IntegerField(default=0, help_text=b'Base id will be filled with leading zeros to this length if zfill is checked.')),
                ('prefix', models.CharField(max_length=256, null=True, blank=True)),
                ('suffix', models.CharField(max_length=256, null=True, blank=True)),
                ('last_id', models.CharField(max_length=256, editable=False)),
                ('next_id', models.CharField(max_length=256, editable=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('creator', models.ForeignKey(related_name='unique_id_creator', to=settings.AUTH_USER_MODEL)),
                ('modifier', models.ForeignKey(related_name='unique_id_modifier', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='nodehandle',
            name='node_type',
            field=models.ForeignKey(to='noclook.NodeType'),
        ),
    ]
