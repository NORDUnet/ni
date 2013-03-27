# -*- coding: utf-8 -*-
"""
Created on 2012-11-22 3:50 PM

@author: lundberg
"""

from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('niweb.apps.userprofile.views',
    url(r'^$', 'list_userprofiles'),
    url(r'^(?P<userprofile_id>\d+)/all$', 'userprofile_detail'),
    url(r'^(?P<userprofile_id>\d+)/$', 'userprofile_detail', {'num_act': 25}),
)
