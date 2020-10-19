# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene


class ModulePermissions(graphene.ObjectType):
    read = graphene.Boolean(required=True)
    list = graphene.Boolean(required=True)
    write = graphene.Boolean(required=True)
    admin = graphene.Boolean(required=True)


class UserPermissions(graphene.ObjectType):
    community = graphene.Field(ModulePermissions)
    network = graphene.Field(ModulePermissions)
    contracts = graphene.Field(ModulePermissions)
