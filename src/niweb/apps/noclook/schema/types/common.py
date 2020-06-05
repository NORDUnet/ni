# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from apps.noclook.models import Dropdown, Choice as ChoiceModel, \
                                Context as ContextModel
from apps.noclook.feeds import context_feed
import apps.noclook.vakt.utils as sriutils
from graphene_django import DjangoObjectType
from apps.noclook.schema.fields import *
from actstream.models import Action as ActionModel


class Dropdown(DjangoObjectType):
    '''
    This class represents a dropdown to use in forms
    '''
    class Meta:
        only_fields = ('id', 'name')
        model = Dropdown


class Neo4jChoice(graphene.ObjectType):
    class Meta:
        interfaces = (KeyValue, )


class TypeInfo(graphene.ObjectType):
    type_name = graphene.String(required=True)
    connection_name = graphene.String(required=True)
    byid_name = graphene.String(required=True)
    all_name = graphene.String(required=True)


class Action(DjangoObjectType):
    '''
    This class represents an Action from the activity log
    '''
    text = graphene.String(required=True)

    def resolve_text(self, info, **kwargs):
        ret = ''

        if self:
            ret = str(self)

        return ret

    class Meta:
        model = ActionModel
        interfaces = (graphene.relay.Node, )
        use_connection = False
        fields = ("actor_content_type", "actor_object_id", "verb",
                    "description", "target_content_type", "target_object_id",
                    "action_object_content_type", "action_object_object_id",
                    "timestamp", "public")


class ActionOrderBy(graphene.Enum):
    timestamp_ASC='timestamp_ASC'
    timestamp_DESC='timestamp_DESC'


class ActionFilter(graphene.InputObjectType):
    context = graphene.String(required=True)


class ActionConnection(graphene.relay.Connection):
    class Meta:
        node = Action


def resolve_available_contexts(self, info, **kwargs):
    return [ x.name for x in ContextModel.objects.all()]


def resolve_context_activity(self, info, **kwargs):
    qs = ActionModel.objects.none()

    if info.context and info.context.user.is_authenticated:
        user = info.context.user

        filter = kwargs.get('filter')
        order_by = kwargs.get('orderBy')

        if ContextModel.objects.filter(name=filter.context).exists():
            # check list permission for this module/context
            context = ContextModel.objects.get(name=filter.context)
            authorized = sriutils.authorize_list_module(user, context)

            if authorized:
                # get readable handle_ids
                readable_ids = sriutils.get_ids_user_canread(user)

                qs = context_feed(filter.context)

                if order_by:
                    if order_by == ActionOrderBy.timestamp_ASC:
                        qs = qs.order_by('timestamp')
                    elif order_by == ActionOrderBy.timestamp_DESC:
                        qs = qs.order_by('-timestamp')
                else:
                    qs = qs.order_by('-timestamp')

                # limit qs to show only readable handle_ids
                qs = qs.filter(actor_object_id__in=readable_ids)
    else:
        raise GraphQLAuthException()

    return qs
