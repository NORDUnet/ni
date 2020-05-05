# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from graphene_django import DjangoObjectType
from apps.noclook.models import Role as RoleModel, RoleGroup as RoleGroupModel
from apps.noclook.schema.core import *
from norduniclient.models import RoleRelationship

class RoleGroup(DjangoObjectType):
    '''
    This class represents a Role in the relational db
    '''
    class Meta:
        model = RoleGroupModel


class Role(DjangoObjectType):
    '''
    This class represents a Role in the relational db
    '''
    class Meta:
        model = RoleModel
        interfaces = (graphene.relay.Node, )
        use_connection = False


class Group(NIObjectType, LogicalMixin):
    '''
    The group type is used to group contacts
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    contacts = NIListField(type_args=(lambda: Contact,), rel_name='Member_of', rel_method='get_relations')
    contact_relations = NIRelationListField(rel_name='Member_of', rel_method='get_relations', graphene_type=lambda: Contact)

    class NIMetaType:
        ni_type = 'Group'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_community_context


class Procedure(NIObjectType, LogicalMixin):
    '''
    The group type is used to group contacts
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()

    class NIMetaType:
        ni_type = 'Procedure'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_community_context


class Address(NIObjectType, LogicalMixin):
    '''
    Phone entity to be used inside contact
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    phone = NIStringField()
    street = NIStringField()
    postal_code = NIStringField()
    postal_area = NIStringField()

    class Meta:
        only_fields = ('handle_id',)

    class NIMetaType:
        ni_type = 'Address'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_community_context


class Organization(NIObjectType, RelationMixin):
    '''
    The group type is used to group contacts
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    organization_number = NIStringField()
    organization_id = NIStringField()
    incident_management_info = NIStringField()
    type = NIChoiceField(dropdown_name="organization_types")
    website = NIStringField()
    addresses = NIListField(type_args=(Address,), rel_name='Has_address', rel_method='get_outgoing_relations')
    addresses_relations = NIRelationListField(rel_name='Has_address', rel_method='get_outgoing_relations', graphene_type= Address)
    affiliation_customer = NIBooleanField()
    affiliation_end_customer = NIBooleanField()
    affiliation_provider = NIBooleanField()
    affiliation_partner = NIBooleanField()
    affiliation_host_user = NIBooleanField()
    affiliation_site_owner = NIBooleanField()
    parent_organization = NISingleRelationField(field_type=(lambda: Organization), rel_name="Parent_of", rel_method="get_relations")
    contacts = NIListField(type_args=(lambda: Contact,), rel_name='Works_for', rel_method='get_relations')
    contacts_relations = NIRelationListField(rel_name='Works_for', rel_method='get_relations', graphene_type=lambda: Contact)

    class NIMetaType:
        ni_type = 'Organization'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_community_context


class RoleRelation(NIRelationType):
    name = graphene.String()
    start = graphene.Field(lambda: Contact)
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


class Phone(NIObjectType, LogicalMixin):
    '''
    Phone entity to be used inside contact
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    type = NIChoiceField(type_kwargs={ 'required': True }, dropdown_name="phone_type")

    class Meta:
        only_fields = ('handle_id',)

    class NIMetaType:
        ni_type = 'Phone'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_community_context


class Email(NIObjectType, LogicalMixin):
    '''
    Email entity to be used inside contact
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    type = NIChoiceField(type_kwargs={ 'required': True }, dropdown_name="email_type")

    class Meta:
        only_fields = ('handle_id',)

    class NIMetaType:
        ni_type = 'Email'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_community_context


class Contact(NIObjectType, RelationMixin):
    '''
    A contact in the SRI system
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    first_name = NIStringField(type_kwargs={ 'required': True })
    last_name = NIStringField(type_kwargs={ 'required': True })
    title = NIStringField()
    salutation = NIStringField()
    contact_type = NIChoiceField(dropdown_name="contact_type")
    phones = NIListField(type_args=(Phone,), rel_name='Has_phone', rel_method='get_outgoing_relations')
    phones_relations = NIRelationListField(rel_name='Has_phone', rel_method='get_outgoing_relations', graphene_type=Phone)
    emails = NIListField(type_args=(Email,), rel_name='Has_email', rel_method='get_outgoing_relations')
    emails_relations = NIRelationListField(rel_name='Has_email', rel_method='get_outgoing_relations', graphene_type=Email)
    pgp_fingerprint = NIStringField()
    member_of_groups = NIListField(type_args=(Group,), rel_name='Member_of', rel_method='get_outgoing_relations')
    roles = NIRelationField(rel_name=RoleRelationship.RELATION_NAME, type_args=(RoleRelation, ))
    organizations = NIListField(type_args=(Organization,), rel_name='Works_for', rel_method='get_outgoing_relations')
    organizations_relations = NIRelationListField(rel_name='Works_for', rel_method='get_outgoing_relations', graphene_type=Organization)
    notes = NIStringField()

    class NIMetaType:
        ni_type = 'Contact'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_community_context


class RoleConnection(graphene.relay.Connection):
    class Meta:
        node = Role


class RoleFilter(graphene.InputObjectType):
    name = graphene.String()
    id = graphene.ID()


class RoleOrderBy(graphene.Enum):
    name_ASC='name_ASC'
    name_DESC='name_DESC'
    handle_id_ASC='handle_id_ASC'
    handle_id_DESC='handle_id_DESC'


community_type_resolver = {
    'Group' : Group,
    'Procedure' : Procedure,
    'Address' : Address,
    'Organization' : Organization,
    'Phone' : Phone,
    'Email' : Email,
    'Contact' : Contact,
    'Contact' : Contact,
}
