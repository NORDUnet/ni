# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from vakt.rules.base import Rule
from apps.noclook.models import NodeHandle, GroupContextAuthzAction, NodeHandleContext

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

        if nodehandle:
            possible_contexts = nodehandle.contexts.filter(pk=self.context.pk)
            if possible_contexts:
                satisfied = True
        else:
            # if the nodehandle comes empty it is a node creation request
            # so other rules may apply but not this one
            satisfied = True

        return satisfied


class ContainsElement(Rule):
    def __init__(self, elem):
        self.elem = elem

    def satisfied(self, list, inquiry=None):
        satisfied = self.elem in list

        return satisfied
