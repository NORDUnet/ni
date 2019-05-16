# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from graphene_django.views import GraphQLView

from .core import *
from .types import *
from .query import *
from .mutations import *

NOCSCHEMA_TYPES = [
    RoleType,
    GroupType,
    ContactType,
    NodeHandleType,
]

NOCSCHEMA_QUERIES = [
    NOCRootQuery,
]

NOCSCHEMA_MUTATIONS = [
    NOCRootMutation,
]


class AuthGraphQLView(LoginRequiredMixin, GraphQLView):
    pass
