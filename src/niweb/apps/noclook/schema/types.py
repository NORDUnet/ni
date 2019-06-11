# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from django.contrib.auth.models import User
from graphene import relay
from .core import *
from ..models import *

def resolve_roles_list(self, info, **kwargs):
    """
    This method is only present here to illustrate how a manual resolver
    could be used
    """
    neo4jnode = self.get_node()
    relations = neo4jnode.get_outgoing_relations()
    roles = relations.get('Is')

    # this may be the worst way to do it, but it's just for a PoC
    handle_id_list = []
    if roles:
        for role in roles:
            role = role['node']
            role_id = role.data.get('handle_id')
            handle_id_list.append(role_id)

    ret = NodeHandle.objects.filter(handle_id__in=handle_id_list)

    return ret

class Role(NIRelationType):
    name = graphene.String(required=True)

    def resolve_name(self, info, **kwargs):
        if self.name:
            return self.name
        else:
            raise Exception('This must not be a role relationship')

    class Meta:
        interfaces = (relay.Node, )

class User(DjangoObjectType):
    '''
    The django user type
    '''
    class Meta:
        model = User
        exclude_fields = ['creator', 'modifier']

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
        only_fields = ('name', 'value')
        model = Choice
        interfaces = (KeyValue, )

class Neo4jChoice(graphene.ObjectType):
    class Meta:
        interfaces = (KeyValue, )

class Group(NIObjectType):
    '''
    The group type is used to group contacts
    '''
    name = NIStringField(type_kwargs={ 'required': True })

    class NIMetaType:
        ni_type = 'Group'
        ni_metatype = 'logical'

class Contact(NIObjectType):
    '''
    A contact in the SRI system
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    first_name = NIStringField(type_kwargs={ 'required': True })
    last_name = NIStringField(type_kwargs={ 'required': True })
    title = NIStringField()
    salutation = NIStringField()
    contact_type = NIStringField()
    phone = NIStringField()
    mobile = NIStringField()
    email = NIStringField()
    other_email = NIStringField()
    PGP_fingerprint = NIStringField()
    member_of_groups = NIListField(type_args=(Group,), rel_name='Member_of', rel_method='get_outgoing_relations')
    works_for = NIRelationField(rel_name='Works_for', type_args=(Role, ))

    class NIMetaType:
        ni_type = 'Contact'
        ni_metatype = 'relation'
