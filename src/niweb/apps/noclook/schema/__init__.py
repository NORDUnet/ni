# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

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

@method_decorator(login_required, name='dispatch')
class AuthGraphQLView(GraphQLView):
    pass
