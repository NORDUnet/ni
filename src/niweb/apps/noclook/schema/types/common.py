# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from apps.noclook.models import Dropdown, Choice as ChoiceModel, \
                                Context as ContextModel
from apps.noclook.feeds import context_feed
import apps.noclook.vakt.utils as sriutils
from apps.noclook.schema.fields import *
from actstream.models import Action as ActionModel
from django.contrib.auth.models import User as UserModel
from graphene_django import DjangoObjectType

from ..metatypes import NINode
from ..core import User


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
    can_create = graphene.Boolean()


class Action(DjangoObjectType):
    '''
    This class represents an Action from the activity log
    '''
    text = graphene.String(required=True)
    action_object = graphene.Field(NINode)
    target_object = graphene.Field(NINode)
    actor = graphene.Field(User)
    actorname = graphene.String()

    def resolve_text(self, info, **kwargs):
        ret = ''

        if self:
            ret = str(self)

        return ret

    def resolve_action_object(self, info, **kwargs):
        ret = None
        contenttype = self.action_object_content_type

        if contenttype and contenttype.app_label == 'noclook' and \
            contenttype.model == 'nodehandle':
            ret = NodeHandle.objects.get(
                handle_id=self.action_object_object_id
            )

        return ret

    def resolve_target_object(self, info, **kwargs):
        ret = None
        contenttype = self.target_content_type

        if contenttype and contenttype.app_label == 'noclook' and \
            contenttype.model == 'nodehandle':
            ret = NodeHandle.objects.get(
                handle_id=self.target_object_id
            )

        return ret

    def resolve_actorname(self, info, **kwargs):
        user = UserModel.objects.get(pk=self.actor_object_id)

        return user.username

    def resolve_actor(self, info, **kwargs):
        '''
        Actor resolver, the user needs admin rights over the node's modules
        '''
        ret = None

        # get action object
        action_object = self.action_object
        # get user

        user = UserModel.objects.get(pk=self.actor_object_id)
        authorized = True

        contexts_names = self.data['noclook']['contexts']
        contexts = [ ContextModel.objects.get(name=x['context_name']) for x in contexts_names]

        if not contexts:
            authorized = False

        for context in contexts:
            is_contextadmin = sriutils.authorize_admin_module(user, context)

            if not is_contextadmin:
                authorized = False

        if authorized:
            ret = user

        return ret

    class Meta:
        model = ActionModel
        interfaces = (graphene.relay.Node, )
        use_connection = False
        fields = ("verb", "description", "timestamp", "public")


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
    '''
    Connection resolver for the activity log, filtered by module name.
    Actions are filtered to only show what the user has rights to list/read
    '''
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
                qs = context_feed(filter.context, user)

                if order_by:
                    if order_by == ActionOrderBy.timestamp_ASC:
                        qs = qs.order_by('timestamp')
                    elif order_by == ActionOrderBy.timestamp_DESC:
                        qs = qs.order_by('-timestamp')
                else:
                    qs = qs.order_by('-timestamp')

    else:
        raise GraphQLAuthException()

    return qs
