# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from norduniclient.models import RoleRelationship
from graphene import relay, ObjectType, String, Field
from .core import *
from ..models import Dropdown as DropdownModel, Choice as ChoiceModel,\
        Role as RoleModel, RoleGroup as RoleGroupModel


class Dropdown(DjangoObjectType):
    '''
    This class represents a dropdown to use in forms
    '''
    class Meta:
        only_fields = ('id', 'name')
        model = DropdownModel


# choice field needs
class NIChoiceField(NIBasicField, ComplexField):
    '''
    Choice type
    '''
    def __init__(self, field_type=Choice, manual_resolver=False,
                    dropdown_name=None, type_kwargs=None, **kwargs):
        self.dropdown_name = dropdown_name
        super(NIChoiceField, self).__init__(field_type, manual_resolver,
                        type_kwargs, **kwargs)

    def get_resolver(self, **kwargs):
        field_name = kwargs.get('field_name')

        if not field_name:
            raise Exception(
                'Field name for field {} should not be empty for a {}'.format(
                    field_name, self.__class__
                )
            )

        dropdown_name = kwargs.get('dropdown_name')

        if not dropdown_name:
            raise Exception(
                'Dropdown name for field {} should not be empty for a {}'.format(
                    field_name, self.__class__
                )
            )

        def resolve_node_value(self, info, **kwargs):
            # resolve dropdown
            dropdown = DropdownModel.objects.get(name=dropdown_name)

            # resolve choice
            node_value = self.get_node().data.get(field_name)
            choice_val = ChoiceModel.objects.filter(
                dropdown=dropdown,
                value=node_value
            ).first()

            return choice_val

        return resolve_node_value


class Neo4jChoice(graphene.ObjectType):
    class Meta:
        interfaces = (KeyValue, )


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


class Group(NIObjectType):
    '''
    The group type is used to group contacts
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    contacts = NIListField(type_args=(lambda: Contact,), rel_name='Member_of', rel_method='get_relations')

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


class Address(NIObjectType):
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


class Organization(NIObjectType):
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
    affiliation_customer = NIBooleanField()
    affiliation_end_customer = NIBooleanField()
    affiliation_provider = NIBooleanField()
    affiliation_partner = NIBooleanField()
    affiliation_host_user = NIBooleanField()
    affiliation_site_owner = NIBooleanField()
    parent_organization = NIListField(type_args=(lambda: Organization,), rel_name='Parent_of', rel_method='get_relations')
    contacts = NIListField(type_args=(lambda: Contact,), rel_name='Works_for', rel_method='get_relations')

    class NIMetaType:
        ni_type = 'Organization'
        ni_metatype = NIMETA_RELATION


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


class Phone(NIObjectType):
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


class Email(NIObjectType):
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


class Contact(NIObjectType):
    '''
    A contact in the SRI system
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    first_name = NIStringField(type_kwargs={ 'required': True })
    last_name = NIStringField(type_kwargs={ 'required': True })
    title = NIStringField()
    salutation = NIStringField()
    contact_type = NIChoiceField(type_kwargs={ 'required': True }, dropdown_name="contact_type")
    phones = NIListField(type_args=(Phone,), rel_name='Has_phone', rel_method='get_outgoing_relations')
    emails = NIListField(type_args=(Email,), rel_name='Has_email', rel_method='get_outgoing_relations')
    pgp_fingerprint = NIStringField()
    member_of_groups = NIListField(type_args=(Group,), rel_name='Member_of', rel_method='get_outgoing_relations')
    roles = NIRelationField(rel_name=RoleRelationship.RELATION_NAME, type_args=(RoleRelation, ))
    organizations = NIListField(type_args=(Organization,), rel_name='Works_for', rel_method='get_outgoing_relations')
    notes = NIStringField()

    class NIMetaType:
        ni_type = 'Contact'
        ni_metatype = NIMETA_RELATION


class ContactWithRolename(ObjectType):
    contact = Field(Contact)
    role = Field(Role)
    relation_id = graphene.Int()


class ContactWithRelation(ObjectType):
    contact = Field(Contact)
    relation_id = graphene.Int()


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
