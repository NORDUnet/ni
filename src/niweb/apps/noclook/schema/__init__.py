# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from graphene_django.views import GraphQLView

from .core import *
from .types import *
from .query import *
from .mutations import *

_nimeta = getattr(NOCRootQuery, 'NIMeta')
graphql_types = getattr(_nimeta, 'graphql_types')

NOCSCHEMA_TYPES = [
    # Interfaces
    NINode,

    # common
    User,
    Dropdown,
    Choice,
    Neo4jChoice,
    NodeHandler,
] + graphql_types

NOCSCHEMA_QUERIES = [
    NOCRootQuery,
]

NOCSCHEMA_MUTATIONS = [
    NOCRootMutation,
]


def login_required_env(f):
    # skip authentication to inspect graphql schema
    if settings.INSPECT_SCHEMA:
        return f
    else:
        return login_required(f)


@method_decorator(login_required_env, name='dispatch')
class AuthGraphQLView(GraphQLView):
    pass
