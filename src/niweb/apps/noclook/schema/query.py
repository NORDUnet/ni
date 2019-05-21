# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
from graphql import GraphQLError
from ..models import Dropdown
from .types import *

class NOCRootQuery(NOCAutoQuery):
    getChoicesForDropdown = graphene.List(Choice, name=graphene.String(required=True))

    def resolve_getChoicesForDropdown(self, info, **kwargs):
        name = kwargs.get('name')
        ddqs = Dropdown.get(name)

        if not isinstance(ddqs, DummyDropdown):
            return ddqs.choice_set.order_by('name')
        else:
            raise Exception(u'Could not find dropdown with name \'{}\'. Please create it using /admin/'.format(name))

    class NIMeta:
        graphql_types = [ Role, Group, Contact ]
