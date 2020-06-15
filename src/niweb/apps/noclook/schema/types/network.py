# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.schema.core import *
from apps.noclook.models import SwitchType as SwitchTypeModel
from .community import Group

## Organizations
class Customer(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    url = NIStringField()
    description = NIStringField()

    class NIMetaType:
        ni_type = 'Customer'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


class EndUser(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    url = NIStringField()
    description = NIStringField()

    class NIMetaType:
        ni_type = 'End User'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


class Provider(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    url = NIStringField()
    description = NIStringField()

    class NIMetaType:
        ni_type = 'Provider'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


class SiteOwner(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    url = NIStringField()
    description = NIStringField()

    class NIMetaType:
        ni_type = 'Site Owner'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


## Cables and Equipment
class Port(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    port_type = NIChoiceField(dropdown_name="port_types")
    description = NIStringField()
    connected_to = NIListField(type_args=(lambda: Physical,), rel_name='Connected_to', rel_method='_incoming')

    class NIMetaType:
        ni_type = 'Port'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class Cable(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    cable_type = NIChoiceField(dropdown_name="cable_types")
    description = NIStringField()
    provider = NISingleRelationField(field_type=(lambda: Provider), rel_name="Provides", rel_method="_incoming")
    ports = NIListField(type_args=(lambda: Port,), rel_name='Connected_to', rel_method='_outgoing')

    class NIMetaType:
        ni_type = 'Cable'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class Host(NIObjectType, PhysicalMixin):
    '''
    A host in the SRI system
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    operational_state = NIStringField(type_kwargs={ 'required': True })
    os = NIStringField()
    os_version = NIStringField()
    vendor = NIStringField()
    backup = NIStringField()
    managed_by = NIStringField()
    ip_addresses = IPAddr()
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
        context_method = sriutils.get_network_context


class Router(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    operational_state = NIChoiceField(dropdown_name="another")
    model = NIStringField()
    version = NIStringField()
    ports = NIListField(type_args=(lambda: Port,), rel_name='Has', rel_method='_outgoing')

    class NIMetaType:
        ni_type = 'Router'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class SwitchType(DjangoObjectType):
    '''
    This class represents a SwitchType for switch's mutations
    '''
    class Meta:
        #only_fields = ('id', 'name')
        model = SwitchTypeModel
        interfaces = (graphene.relay.Node, )


def resolve_getSwitchTypes(self, info, **kwargs):
    if info.context and info.context.user.is_authenticated:
        return SwitchTypeModel.objects.all()
    else:
        raise GraphQLAuthException()


class Switch(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    operational_state = NIStringField(type_kwargs={ 'required': True })
    ip_addresses = IPAddr()
    responsible_group = NISingleRelationField(field_type=(lambda: Group), rel_name="Responsible", rel_method="_incoming")
    support_group = NISingleRelationField(field_type=(lambda: Group), rel_name="Support", rel_method="_incoming")
    managed_by = NIStringField()
    backup = NIStringField()
    os = NIStringField()
    os_version = NIStringField()
    contract_number = NIStringField()
    rack_units = NIIntField() # Equipment height
    rack_position = NIIntField()

    class NIMetaType:
        ni_type = 'Switch'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context

## Peering
class PeeringPartner(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    as_number = NIStringField()

    class NIMetaType:
        ni_type = 'Peering Partner'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


class PeeringGroup(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })

    class NIMetaType:
        ni_type = 'Peering Group'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_network_context


network_type_resolver = {
    'Customer': Customer,
    'End User': EndUser,
    'Peering Partner': PeeringPartner,
    'Peering Group': PeeringGroup,
    'Provider': Provider,
    'Site Owner': SiteOwner,
    'Port': Port,
    'Cable': Cable,
    'Host': Host,
    'Switch': Switch,
}
