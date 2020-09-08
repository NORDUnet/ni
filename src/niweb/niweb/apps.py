# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from django.contrib.admin.apps import AdminConfig


class SRIAdminConfig(AdminConfig):
    default_site = 'niweb.admin.SRIAdminSite'
