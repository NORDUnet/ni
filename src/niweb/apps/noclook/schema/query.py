# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
from graphql import GraphQLError
from ..models import Dropdown
from .types import *
from .core import get_logger_user

class NOCRootQuery(NOCAutoQuery):
    viewer = graphene.Field(UserType)
    getChoicesForDropdown = graphene.List(ChoiceType, name=graphene.String(required=True))
    rolesconn = graphene.relay.ConnectionField(RoleConnection)

    def resolve_rolesconn(self, info, **kwargs):
        node_type = NodeType.objects.filter(type='Role').first()
        return NodeHandle.objects.filter(node_type=node_type)

    # viewer field for relay
    def resolve_viewer(self, info, **kwargs):
        user = get_logger_user()
        return user

    def resolve_getChoicesForDropdown(self, info, **kwargs):
        name = kwargs.get('name')
        ddqs = Dropdown.get(name)

        if not isinstance(ddqs, DummyDropdown):
            return ddqs.choice_set.order_by('name')
        else:
            raise Exception(u'Could not find dropdown with name \'{}\'. Please create it using /admin/'.format(name))

    class NIMeta:
        graphql_types = [ RoleType, GroupType, ContactType ]
