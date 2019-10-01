# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from vakt.rules.base import Rule
from apps.noclook.models import GroupContextAuthzAction, NodeHandleContext

class HasAuthAction(Rule):
    def __init__(self, authzaction, context):
        self.authzaction = authzaction
        self.context = context

    def satisfied(self, user, inquiry=None):
        satisfied = False

        # get user groups
        groups = user.groups.all()

        # get all authzactions for these groups and context
        gcaas = GroupContextAuthzAction.objects.filter(
            group__in=groups,
            context=self.context,
            authzprofile=self.authzaction
        )

        if gcaas:
            satisfied = True

        return satisfied


class BelongsContext(Rule):
    def __init__(self, context):
        self.context = context

    def satisfied(self, nodehandle, inquiry=None):
        satisfied = False

        nhctxs = NodeHandleContext.objects.filter(
            nodehandle=nodehandle,
            context=self.context,
        )

        if nhctxs:
            satisfied = True

        return satisfied
