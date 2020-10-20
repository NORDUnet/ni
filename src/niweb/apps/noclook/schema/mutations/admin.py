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
        # get user
        user_id = input.get("user")
        user_id = graphene.relay.Node.from_global_id(user_id)[1]

        edit_user = User.objects.get(id=user_id)

        # get context
        context_name = input.get("context")
        contexts = sriutils.get_all_contexts()
        context = contexts.get(context_name, None)

        # check if the user is admin for the specified module
        success=False
        errors=None
        user_permissions = None

        try:
            if info.context and info.context.user.is_authenticated:
                if user and context:
                    if sriutils.authorize_superadmin(user) or \
                        sriutils.authorize_admin_module(user, context):

                        read = input.get("read", None)
                        write = input.get("write", None)
                        list = input.get("list", None)
                        admin = input.get("admin", None)

                        # only superadmins can grant admin permission
                        if admin != None:
                            aaction = sriutils.get_admin_authaction()
                            if sriutils.authorize_superadmin(user):
                                sriutils.edit_aaction_context_user(
                                    aaction, context, edit_user, admin)
                                success=True
                            else:
                                errors = [
                                    ErrorType(field="_",
                                        messages=[ \
                                        "Only superadmins can grant admin rights" \
                                            .format(node_type)])
                                ]
                                success=False

                        # perform the rest of the operations only if we had
                        # succeeeded on the previous operation
                        if success:
                            if read != None:
                                aaction = sriutils.get_read_authaction()
                                sriutils.edit_aaction_context_user(
                                    aaction, context, edit_user, read)
                                success=True

                            if write != None:
                                aaction = sriutils.get_write_authaction()
                                sriutils.edit_aaction_context_user(
                                    aaction, context, edit_user, write)
                                success=True

                            if list != None:
                                aaction = sriutils.get_list_authaction()
                                sriutils.edit_aaction_context_user(
                                    aaction, context, edit_user, list)
                                success=True

                        user_permissions = sriutils.get_user_permissions(edit_user)
        except:
            errors = [
                ErrorType(
                    field="_",
                    messages=["A {} with that name already exists." \
                        .format(node_type)])
            ]

        ret = GrantUserPermission(success=success, errors=errors,
                user_permissions=user_permissions)

        return ret


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
