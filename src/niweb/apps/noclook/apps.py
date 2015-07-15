# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.apps import AppConfig
from actstream import registry
from django.contrib.auth.models import User, Group
from django_comments.models import Comment


class NOCLookConfig(AppConfig):
    name = 'apps.noclook'

    def ready(self):
        registry.register(User)
        registry.register(Group)
        registry.register(Comment)
        registry.register(self.get_model('Nodehandle'))

