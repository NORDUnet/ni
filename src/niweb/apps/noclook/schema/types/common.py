# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from apps.noclook.models import Dropdown, Choice
from apps.noclook.schema.core import KeyValue
from graphene_django import DjangoObjectType

class Dropdown(DjangoObjectType):
    '''
    This class represents a dropdown to use in forms
    '''
    class Meta:
        only_fields = ('id', 'name')
        model = Dropdown


class Choice(DjangoObjectType):
    '''
    This class is used for the choices available in a dropdown
    '''
    class Meta:
        model = Choice
        interfaces = (KeyValue, )


class Neo4jChoice(graphene.ObjectType):
    class Meta:
        interfaces = (KeyValue, )
