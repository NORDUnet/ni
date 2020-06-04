# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from tastypie.resources import Resource, ModelResource
from tastypie import fields
from tastypie.authentication import SessionAuthentication
from tastypie.authorization import Authorization
from apps.userprofile.models import UserProfile

class UserProfileResource(ModelResource):

    class Meta:
        queryset = UserProfile.objects.all()
        resource_name = 'userprofile'
        authentication = SessionAuthentication()
        authorization = Authorization()
        excludes = ['created', 'modified']
        filtering = {}

    user_id = fields.IntegerField('user_id')
    email = fields.CharField('email')
    display_name = fields.CharField('display_name', blank=True, null=True)
    #  avatar = fields.FileField('avatar')
    landing_page = fields.CharField('landing_page')
    view_network = fields.BooleanField('view_network')
    view_services = fields.BooleanField('view_services')
    view_community = fields.BooleanField('view_community')
