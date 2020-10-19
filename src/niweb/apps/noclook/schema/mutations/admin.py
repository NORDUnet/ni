# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.schema.core import CommentType
from apps.noclook.schema.types import *
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from graphene import relay
from graphene import Field

import graphene

## mutation for the users to edit their preferences

## mutations for admins,
# to grant or revoke permissions from users
class GrantUserPermission(relay.ClientIDMutation):
    class Input:
        user = graphene.ID(required=True)
        context = graphene.String(required=True)
        read = graphene.Boolean()
        write = graphene.Boolean()
        list = graphene.Boolean()
        admin = graphene.Boolean()

    success = graphene.Boolean()
    errors = graphene.List(ErrorType)
    user_permissions = graphene.Field(UserPermissions)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user_id = input.get("user")
        user_id = graphene.relay.Node.from_global_id(user_id)[1]

        user = User.objects.get(id=user_id)

        return GrantUserPermission(success=False, errors=None)


# set context to a nodehandle list
class SetNodesContext(relay.ClientIDMutation):
    class Input:
        context = graphene.String(required=True)
        nodes = graphene.List(graphene.NonNull(graphene.ID))

    success = graphene.Boolean()
    errors = graphene.List(ErrorType)
    nodes = graphene.List(NINode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        return SetNodesContext(success=False, errors=None, nodes=[])
