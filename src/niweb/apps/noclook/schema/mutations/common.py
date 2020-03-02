# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.schema.core import CommentType
from apps.noclook.models import Dropdown as DropdownModel, Choice as ChoiceModel
from apps.noclook.schema.types import *
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from graphene import relay
from graphene import Field

import graphene

class CreateComment(relay.ClientIDMutation):
    class Input:
        object_id = graphene.ID(required=True)
        comment = graphene.String(required=True)

    comment = Field(CommentType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        object_id = input.get("object_id")
        object_pk = relay.Node.from_global_id(object_id)[1]

        # check it can write for this node
        authorized = sriutils.authorice_write_resource(info.context.user, object_pk)

        if not authorized:
            raise GraphQLAuthException()

        comment = input.get("comment")
        content_type = ContentType.objects.get(app_label="noclook", model="nodehandle")

        request_factory = RequestFactory()
        request = request_factory.post('/', data={})
        site = get_current_site(request)

        comment = Comment(
            content_type=content_type,
            object_pk=object_pk,
            site=site,
            user=info.context.user,
            comment=comment,
        )
        comment.save()

        return CreateComment(comment=comment)

class UpdateComment(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        comment = graphene.String(required=True)

    comment = Field(CommentType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        id = input.get("id")
        id = relay.Node.from_global_id(id)[1]
        comment_txt = input.get("comment")

        comment = Comment.objects.get(id=id)
        object_pk = comment.object_pk

        # check it can write for this node
        authorized = sriutils.authorice_write_resource(info.context.user, object_pk)

        if not authorized:
            raise GraphQLAuthException()

        comment.comment = comment_txt
        comment.save()

        return UpdateComment(comment=comment)

class DeleteComment(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    success = graphene.Boolean(required=True)
    id = graphene.ID(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        relay_id = input.get("id")
        id = relay.Node.from_global_id(relay_id)[1]
        success = False

        try:
            comment = Comment.objects.get(id=id)
            object_pk = comment.object_pk

            # check it can write for this node
            authorized = sriutils.authorice_write_resource(info.context.user, object_pk)

            if not authorized:
                raise GraphQLAuthException()

            comment.delete()
            success = True
        except ObjectDoesNotExist:
            success = False

        return DeleteComment(success=success, id=relay_id)


class CreateOptionForDropdown(relay.ClientIDMutation):
    class Input:
        dropdown_name = graphene.String(required=True)
        name = graphene.String(required=True)
        value = graphene.String(required=True)

    choice = Field(Choice)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        # only superadmins may add options for dropdowns
        authorized = sriutils.authorize_superadmin(info.context.user)

        if not authorized:
            raise GraphQLAuthException()

        dropdown_name = input.get("dropdown_name")
        name  = input.get("name")
        value = input.get("value")
        dropdown = DropdownModel.objects.get(name=dropdown_name)

        choice = ChoiceModel(
            dropdown=dropdown,
            name=name,
            value=value
        )
        choice.save()

        return CreateOptionForDropdown(choice=choice)
