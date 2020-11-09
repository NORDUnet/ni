# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.userprofile.models import UserProfile as DjangoUserProfile
from django.contrib.auth.models import User as DjangoUser
from graphene_django import DjangoObjectType
from ..core import User

import graphene


# connection classes
class UserConnection(graphene.relay.Connection):
    class Meta:
        node = User


class UserFilter(graphene.InputObjectType):
    username_contains = graphene.String()


class UserOrder(graphene.Enum):
    username_ASC = 'username_ASC'
    username_DESC = 'username_DESC'


class LandingPage(graphene.Enum):
    NETWORK = 'Network'
    SERVICES = 'Services'
    COMMUNITY = 'Community'


class UserProfile(DjangoObjectType):
    landing_page = graphene.Field(LandingPage)

    class Meta:
        model = DjangoUserProfile


# resolvers
def resolve_getUserPermissions(self, info, **kwargs):
    ret = None

    if info.context and info.context.user.is_authenticated:
        current_user = info.context.user
        ret = get_user_permissions(current_user)

        return ret
    else:
        raise GraphQLAuthException()


def resolve_getUserById(self, info, **kwargs):
    ret = None
    id = kwargs.get('ID', None)

    # all authenticated users can query an user by id
    # but they won't see sensitive data (like permissions)
    if info.context and info.context.user.is_authenticated:
        if id and DjangoUser.objects.filter(id=id):
            ret = DjangoUser.objects.get(id=id)
    else:
        raise GraphQLAuthException()

    return ret


def resolve_users(self, info, **kwargs):
    ret = []
    filter = kwargs.get('filter', {})
    orderBy = kwargs.get('orderBy', None)

    # all authenticated users can query the user list
    if info.context and info.context.user.is_authenticated:
        ret = DjangoUser.objects.all().order_by('id')

        # filter by name
        filter_name_contains = filter.get('username_contains', None)
        if filter_name_contains:
            ret = ret.filter(username__icontains=filter_name_contains)

        # order
        if orderBy:
            order = orderBy.split('_')[1]
            if order == 'ASC':
                ret = ret.order_by('-username')
            elif order == 'DESC':
                ret = ret.order_by('username')
    else:
        raise GraphQLAuthException()

    return ret
