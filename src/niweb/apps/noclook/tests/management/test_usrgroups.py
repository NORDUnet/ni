# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from django.core.management import call_command
from django.contrib.auth.models import User, Group

from ..neo4j_base import NeoTestCase

class UsrGroupTest(NeoTestCase):
    cmd_name = 'usrgroups'
    username = 'newadmin'
    password = 'norduni'

    def test_usrgroups_cmd(self):
        # create user
        user = User.objects.create_user(
            self.username,
            password=self.username
        )

        user.is_superuser = True
        user.is_staff = False
        user.save()

        # check that doesn't have groups assigned
        group_lst = list(user.groups.values_list('name', flat=True))
        self.assertEquals(group_lst, [])

        # call command
        call_command(
            self.cmd_name,
            username=self.username,
            verbosity=0,
        )

        # check that it has groups assigned
        group_lst = list(user.groups.values_list('name', flat=True))
        self.assertNotEquals(group_lst, [])
