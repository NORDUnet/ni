# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from graphene_django.views import GraphQLView

from .core import *
from .types import *
from .query import *
from .mutations import *

NOCSCHEMA_TYPES = [
    # Interfaces
    NINode,

    # common
    User,
    Dropdown,
    Choice,
    Neo4jChoice,
    NodeHandler,

    # Community
    Group,
    Contact,
    Procedure,
    Address,
    Phone,
    Email,

    # Network
    ## organizations
    Customer,
    EndUser,
    Provider,
    SiteOwner,

    ## cables equipement
    Port,
    Host,
    Cable,

    ## Peering
    PeeringGroup,
    PeeringPartner,
]

NOCSCHEMA_QUERIES = [
    NOCRootQuery,
]

NOCSCHEMA_MUTATIONS = [
    NOCRootMutation,
]

@method_decorator(login_required, name='dispatch')
class AuthGraphQLView(GraphQLView):
    pass
