# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from django.contrib import admin


class SRIAdminSite(admin.AdminSite):
    site_url = '/dashboard'
