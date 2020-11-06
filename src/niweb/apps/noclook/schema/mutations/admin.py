# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.schema.core import CommentType
from apps.noclook.schema.types import *
from apps.noclook.models import Context as DjangoContext
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User as DjangoUser
from django.contrib.sites.shortcuts import get_current_site
from graphene import relay
from graphene import Field
from binascii import Error as BinasciiError

from ..core import User

import graphene

## mutation for the users to edit their preferences

## mutations for admins,
# to grant or revoke permissions from users
class GrantUserPermission(relay.ClientIDMutation):
    class Input:
        user_id = graphene.ID(required=True)
        context = graphene.String(required=True)
        read = graphene.Boolean()
        write = graphene.Boolean()
        list = graphene.Boolean()
        admin = graphene.Boolean()

    success = graphene.Boolean()
    errors = graphene.List(ErrorType)
    user = graphene.Field(User)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        # get user
        user_id = input.get("user_id")

        # we'll enable this line once we've changed id to the relay format
        #user_id = graphene.relay.Node.from_global_id(user_id)[1]

        edit_user = DjangoUser.objects.get(id=user_id)

        # get context
        context_name = input.get("context").lower()
        contexts = sriutils.get_all_contexts()
        context = contexts.get(context_name, None)

        # check if the user is admin for the specified module
        success=True
        errors=None

        if info.context and info.context.user.is_authenticated:
            try:
                logged_user = info.context.user

                if edit_user and context:
                    if sriutils.authorize_superadmin(logged_user) or \
                        sriutils.authorize_admin_module(logged_user, context):

                        read = input.get("read", None)
                        write = input.get("write", None)
                        list = input.get("list", None)
                        admin = input.get("admin", None)

                        # only superadmins can grant admin permission
                        if admin != None:
                            aaction = sriutils.get_admin_authaction()
                            if sriutils.authorize_superadmin(logged_user):
                                sriutils.edit_aaction_context_user(
                                    aaction, context, edit_user, admin)
                                success=True
                            else:
                                errors = [
                                    ErrorType(field="_",
                                        messages=[ \
                                        "Only superadmins can grant admin rights"])
                                ]
                                success=False

                        # perform the rest of the operations only if we had
                        # succeeeded on the previous operation
                        if success:
                            if read != None:
                                aaction = sriutils.get_read_authaction()
                                sriutils.edit_aaction_context_user(
                                    aaction, context, edit_user, read)

                            if write != None:
                                aaction = sriutils.get_write_authaction()
                                sriutils.edit_aaction_context_user(
                                    aaction, context, edit_user, write)

                            if list != None:
                                aaction = sriutils.get_list_authaction()
                                sriutils.edit_aaction_context_user(
                                    aaction, context, edit_user, list)
                    else:
                        success = False
                else:
                    success = False
            except Exception as e:
                import traceback

                errors = [
                    ErrorType(
                        field="_",
                        messages=\
                            ["An error occurred while processing your request"])
                ]
                success = False
        else:
            raise GraphQLAuthException()

        ret = GrantUserPermission(success=success, errors=errors,
                user=edit_user)

        return ret


class GrantUsersPermission(relay.ClientIDMutation):
    class Input:
        users_ids = graphene.List(graphene.NonNull(graphene.ID, \
            required=True))
        context = graphene.String(required=True)
        read = graphene.Boolean()
        write = graphene.Boolean()
        list = graphene.Boolean()
        admin = graphene.Boolean()

    results = graphene.List(GrantUserPermission)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context or not info.context.user.is_authenticated:
            raise GraphQLAuthException()

        # get input values
        users_ids = input.get("users_ids")
        context = input.get("context")
        read = input.get("read")
        write = input.get("write")
        list = input.get("list")
        admin = input.get("admin")

        results = []

        for user_id in users_ids:
            subinput = dict(
                user_id=user_id,
                context=context,
                read=read,
                write=write,
                list=list,
                admin=admin,
            )

            ret = \
                GrantUserPermission.mutate_and_get_payload(root, info, **subinput)
            results.append(ret)

        return cls(results=results)


# edit user profile
class EditUserProfile(relay.ClientIDMutation):
    class Input:
        user_id = graphene.ID(required=True)
        first_name = graphene.String()
        last_name = graphene.String()
        email = graphene.String()
        is_staff = graphene.Boolean()
        is_active = graphene.Boolean()
        landing_page = graphene.Field(LandingPage)
        view_network = graphene.Boolean()
        view_services = graphene.Boolean()
        view_community = graphene.Boolean()

    success = graphene.Boolean()
    errors = graphene.List(ErrorType)
    user = graphene.Field(UserProfile)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pass


# set context to a nodehandle list
class SetNodesContext(relay.ClientIDMutation):
    class Input:
        contexts = graphene.List(graphene.NonNull(graphene.String, \
            required=True))
        nodes = graphene.List(graphene.NonNull(graphene.ID))

    success = graphene.Boolean()
    errors = graphene.List(ErrorType)
    nodes = graphene.List(NINode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        success = False
        nodes = []
        errors = []

        nodes_ids = input.get("nodes", [])
        contexts_names = input.get("contexts")

        if not DjangoContext.objects.filter(name__in=contexts_names).exists():
            errors.append(
                ErrorType(
                    field=node_id,
                    messages=\
                        ["The context {} doesn't exists".format(contexts_names)]
                    )
                )
            return SetNodesContext(success=success, errors=errors, nodes=nodes)

        contexts = DjangoContext.objects.filter(name__in=contexts_names)

        if info.context and info.context.user.is_authenticated:
            # check if we have rights over the context
            final_contexts = contexts
            for context in contexts:
                authorized_c = sriutils.authorize_admin_module(info.context.user,
                                context)
                if not authorized_c:
                    # remove context from list
                    final_contexts.remove(context)


            if not final_contexts:
                errors.append(
                    ErrorType(
                        field=node_id,
                        messages=\
                            ["You need admin rights to perform this operation"]
                        )
                    )
                return SetNodesContext(success=success, errors=errors,
                        nodes=nodes)

            success = True

            for node_id in nodes_ids:
                # get node
                try:
                    handle_id = graphene.relay.Node.from_global_id(node_id)[1]

                    # check that the user have write rights over the
                    if sriutils.authorice_write_resource(info.context.user,
                        handle_id):

                        nh = NodeHandle.objects.get(handle_id=handle_id)
                        sriutils.set_nodehandle_contexts(contexts, nh)
                        nodes.append(nh)
                    else:
                        errors.append(
                            ErrorType(
                                field=node_id,
                                messages=\
                                    ["You don't have write rights for node id {}"
                                        .format(node_id)]
                                )
                            )

                except BinasciiError:
                    errors.append(
                        ErrorType(
                            field=node_id,
                            messages=\
                                ["The id {} ".format(node_id)]
                            )
                        )
        else:
            raise GraphQLAuthException()

        return SetNodesContext(success=success, errors=errors, nodes=nodes)
