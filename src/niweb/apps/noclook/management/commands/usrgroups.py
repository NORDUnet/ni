# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import Context
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from django.conf import settings

import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Add an specific user to the permission groups.'

    def add_arguments(self, parser):
        parser.add_argument("--username",
                    help="Which user should be added to this groups", type=str, default="admin")


    def handle(self, *args, **options):
        if options['username']:
            username = options['username']
            self.add_groups(username)
            return

    def add_groups(self, username):
        user = User.objects.filter(username=username)

        if user:
            user = User.objects.get(username=username)
            contexts = Context.objects.all()

            for context in contexts:
                gr_name = 'read_{}'.format(context.name.lower())
                gw_name = 'write_{}'.format(context.name.lower())
                gl_name = 'list_{}'.format(context.name.lower())
                ga_name = 'admin_{}'.format(context.name.lower())

                group_names = [gr_name, gw_name, gl_name, ga_name]

                for group_name in group_names:
                    if Group.objects.filter(name=group_name):
                        group = Group.objects.get(name=group_name)
                        group.user_set.add(user)
