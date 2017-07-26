# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.apps import AppConfig


class NOCLookConfig(AppConfig):
    name = 'apps.noclook'

    def ready(self):
        from actstream import registry
        from django.contrib.auth.models import User, Group
        from django_comments.models import Comment
        registry.register(User)
        registry.register(Group)
        registry.register(Comment)
        registry.register(self.get_model('Nodehandle'))

