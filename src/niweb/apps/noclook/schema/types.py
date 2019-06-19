# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from norduniclient.models import RoleRelationship
from django.contrib.auth.models import User
from graphene import relay
from .core import *
from ..models import *

# further centralization?
NIMETA_LOGICAL  = 'logical'
NIMETA_RELATION = 'relation'
NIMETA_PHYSICAL = 'physical'
NIMETA_LOCATION = 'location'

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
        ni_metatype = NIMETA_LOGICAL

class Procedure(NIObjectType):
    '''
    The group type is used to group contacts
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()

    class NIMetaType:
        ni_type = 'Procedure'
        ni_metatype = NIMETA_LOGICAL

class Organization(NIObjectType):
    '''
    The group type is used to group contacts
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField(type_kwargs={ 'required': True })
    phone = NIStringField()
    website = NIStringField()
    customer_id = NIStringField()
    additional_info = NIStringField()

    class NIMetaType:
        ni_type = 'Organization'
        ni_metatype = NIMETA_RELATION

class Role(NIRelationType):
    name = graphene.String(required=True)
    organization = graphene.Field(Organization)

    def resolve_name(self, info, **kwargs):
        if self.name:
            return self.name
        else:
            raise Exception('This must not be a role relationship')

    def resolve_organization(self, info, **kwargs):
        return NodeHandle.objects.get(handle_id=self.end)

    class NIMeta:
        nimodel = RoleRelationship

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
    roles = NIRelationField(rel_name='Works_for', type_args=(Role, ))

    class NIMetaType:
        ni_type = 'Contact'
        ni_metatype = NIMETA_RELATION

class Host(NIObjectType):
    '''
    A host in the SRI system
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    operational_state = NIStringField(type_kwargs={ 'required': True })
    os = NIStringField()
    os_version = NIStringField()
    vendor = NIStringField()
    backup = NIStringField()
    managed_by = NIStringField()
    ip_addresses = IPAddr()
    description = NIStringField()
    responsible_group = NIStringField()
    support_group = NIStringField()
    security_class = NIStringField()
    security_comment = NIStringField()

    def resolve_ip_addresses(self, info, **kwargs):
        '''Manual resolver for the ip field'''
        return self.get_node().data.get('ip_addresses', None)

    class NIMetaType:
        ni_type = 'Host'
        ni_metatype = NIMETA_LOGICAL
