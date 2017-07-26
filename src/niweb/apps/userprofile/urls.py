# -*- coding: utf-8 -*-
"""
Created on 2012-11-22 3:50 PM

@author: lundberg
"""

from django.conf.urls import url
from . import views

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    url(r'^$', views.list_userprofiles),
    url(r'^(?P<userprofile_id>\d+)/$', views.userprofile_detail),
]
