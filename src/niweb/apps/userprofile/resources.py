# -*- coding: utf-8 -*-

import logging

from tastypie.resources import Resource, ModelResource
from tastypie import fields
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import Authorization
from apps.userprofile.models import UserProfile


logger = logging.getLogger('userprofile_resources')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class UserProfileResource(ModelResource):
    
    class Meta:
        queryset = UserProfile.objects.all()
        resource_name = 'userprofile'
        # XXX fix authentication = ApiKeyAuthentication()
        authorization = Authorization()
        excludes = ['created', 'modified']
        filtering = {}
    
    display_name = fields.CharField('display_name')
    email = fields.CharField('user__email')
    #  avatar = fields.FileField('avatar')
    landing_page = fields.CharField('landing_page')
    view_network = fields.BooleanField('view_network')
    view_services = fields.BooleanField('view_services')
    view_community = fields.BooleanField('view_community')
