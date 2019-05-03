# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
from graphql import GraphQLError
from .types import *

class NOCRootQuery(NOCAutoQuery):
    pass

    class NIMeta:
        graphql_types = [ RoleType, GroupType, ContactType ]
