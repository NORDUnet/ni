# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

## metatype interfaces
class Logical(graphene.Interface):
    name = graphene.String()


class Relation(graphene.Interface):
    name = graphene.String()


class Physical(graphene.Interface):
    name = graphene.String()


class Location(graphene.Interface):
    name = graphene.String()
