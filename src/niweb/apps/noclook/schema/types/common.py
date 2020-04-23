# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from apps.noclook.models import Dropdown, Choice as ChoiceModel
from graphene_django import DjangoObjectType
from apps.noclook.schema.fields import *

class Dropdown(DjangoObjectType):
    '''
    This class represents a dropdown to use in forms
    '''
    class Meta:
        only_fields = ('id', 'name')
        model = Dropdown


class Neo4jChoice(graphene.ObjectType):
    class Meta:
        interfaces = (KeyValue, )
