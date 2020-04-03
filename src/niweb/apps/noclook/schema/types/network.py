# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.schema.core import *

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
    port_type = NIChoiceField()
    description = NIStringField()
    connected_to = NIListField(type_args=(lambda: Physical,), rel_name='Connected_to', rel_method='_incoming')

    class NIMetaType:
        ni_type = 'Port'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class Cable(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    cable_type = NIChoiceField()
    description = NIStringField()
    providers = NIListField(type_args=(lambda: Provider,), rel_name='Provides', rel_method='_incoming')
    providers_relations = NIRelationListField(rel_name='Provides', rel_method='_incoming', graphene_type=lambda: Provider)
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
        context_method = sriutils.get_network_context


class Router(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    operational_state = NIChoiceField()
    model = NIStringField()
    version = NIStringField()
    ports = NIListField(type_args=(lambda: Port,), rel_name='Has', rel_method='_outgoing')

    class NIMetaType:
        ni_type = 'Router'
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
}
