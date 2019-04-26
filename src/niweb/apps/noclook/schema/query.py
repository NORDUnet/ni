# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
from .types import *

class NOCRootQuery(graphene.ObjectType):
    node = NIRelayNode.Field()
    roles = graphene.List(RoleType, limit=graphene.Int())
    groups = graphene.List(GroupType, limit=graphene.Int())
    contacts = graphene.List(ContactType, limit=graphene.Int())

    def resolve_roles(self, info, **args):
        limit = args.get('limit', False)
        type = NodeType.objects.get(type="Role") # TODO too raw
        if limit:
            return NodeHandle.objects.filter(node_type=type)[:10]
        else:
            return NodeHandle.objects.filter(node_type=type)

    def resolve_groups(self, info, **args):
        limit = args.get('limit', False)
        type = NodeType.objects.get(type="Group") # TODO too raw
        if limit:
            return NodeHandle.objects.filter(node_type=type)[:10]
        else:
            return NodeHandle.objects.filter(node_type=type)

    def resolve_contacts(self, info, **args):
        limit = args.get('limit', False)
        type = NodeType.objects.get(type="Contact") # TODO too raw
        if limit:
            return NodeHandle.objects.filter(node_type=type)[:10]
        else:
            return NodeHandle.objects.filter(node_type=type)
