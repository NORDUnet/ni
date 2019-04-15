# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

class Query(graphene.ObjectType):
    roles = graphene.List(RoleType, limit=graphene.Int())
    contacts = graphene.List(ContactType, limit=graphene.Int())

    def resolve_roles(self, info, **args):
        limit = args.get('limit', False)
        type = NodeType.objects.get(type="Role") # TODO too raw
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
