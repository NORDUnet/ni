# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from norduniclient.models import RoleRelationship
from graphene import relay
from .core import *
from ..models import Dropdown, Choice, Role as RoleModel

# further centralization?
NIMETA_LOGICAL  = 'logical'
NIMETA_RELATION = 'relation'
NIMETA_PHYSICAL = 'physical'
NIMETA_LOCATION = 'location'


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

class Role(DjangoObjectType):
    '''
    This class represents a Role in the relational db
    '''
    class Meta:
        model = RoleModel

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
    incident_management_info = NIStringField()
    type = NIChoiceField()

    class NIMetaType:
        ni_type = 'Organization'
        ni_metatype = NIMETA_RELATION

class RoleRelation(NIRelationType):
    name = graphene.String()
    end = graphene.Field(Organization)
    role_data = graphene.Field(Role)

    def resolve_name(self, info, **kwargs):
        return getattr(self, 'name', None)

    def resolve_role_data(self, info, **kwargs):
        name = getattr(self, 'name', None)
        role_data = RoleModel.objects.get(name=name)
        return role_data

    class NIMetaType:
        nimodel = RoleRelationship
        filter_exclude = ('type')

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
    roles = NIRelationField(rel_name=RoleRelationship.RELATION_NAME, type_args=(RoleRelation, ))
    notes = NIStringField()

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


class RoleConnection(relay.Connection):
    class Meta:
        node = Role


class RoleFilter(graphene.InputObjectType):
    name = graphene.String()
    handle_id = graphene.Int()


class RoleOrderBy(graphene.Enum):
    name_ASC='name_ASC'
    name_DESC='name_DESC'
    handle_id_ASC='handle_id_ASC'
    handle_id_DESC='handle_id_DESC'
