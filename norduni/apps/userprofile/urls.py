# -*- coding: utf-8 -*-
"""
Created on 2012-11-22 3:50 PM

@author: lundberg
"""

from django.urls import path
from . import views

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    path('', views.list_userprofiles),
    path('<int:userprofile_id>/', views.userprofile_detail, name='userprofile_detail'),
]
