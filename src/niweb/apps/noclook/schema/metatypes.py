# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

## metatype interfaces
class Logical(graphene.Interface):
    name = graphene.String(required= True)


class Relation(graphene.Interface):
    name = graphene.String(required= True)


class Physical(graphene.Interface):
    name = graphene.String(required= True)


class Location(graphene.Interface):
    name = graphene.String(required= True)
