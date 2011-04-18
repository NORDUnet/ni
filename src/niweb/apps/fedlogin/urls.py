# -*- coding: utf-8 -*-
"""
Created on Mon Apr 11 13:23:23 2011

@author: lundberg
"""

from django.conf.urls.defaults import *
from django.contrib.auth.views import login

urlpatterns = patterns('',
    #Fedlogin
    url(r'^login/$', login, {'template_name': 'login.html'}, 'login'),
    url(r'^logout/$', 'niweb.apps.fedlogin.views.fedlogout', name='logout'),
    url(r'^login-federated/$', 'niweb.apps.fedlogin.views.fedlogin', name='loginfed'),
)