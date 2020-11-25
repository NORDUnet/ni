# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import norduniclient as nc

from apps.noclook.schema.core import *
from apps.noclook.models import SwitchType as SwitchTypeModel, \
                                ServiceType as ServiceTypeModel, \
                                ServiceClass as ServiceClassModel
from apps.noclook.schema.utils import sunet_forms_enabled
from .community import Group, Address

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


class HostUser(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    url = NIStringField()
    description = NIStringField()

    class NIMetaType:
        ni_type = 'Host User'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


## Cables and Equipment
class Unit(NIObjectType, LogicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    vlan = NIStringField()
    ip_address = graphene.String() # only for PeeringGroup's "dependencies" list

    def resolve_ip_address(self, info, **kwargs):
        '''Manual resolver for the ip field'''
        ret = None

        if hasattr(self, 'relation_id'):
            rel = nc.get_relationship_bundle(nc.graphdb.manager, self.relation_id)
            ret = rel['data'].get('ip_address', None)

        return ret

    class NIMetaType:
        ni_type = 'Unit'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_network_context
        can_create = False


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
    cable_length = NIFloatField()
    provider = NISingleRelationField(field_type=(lambda: Provider), \
        rel_name="Provides", rel_method="_incoming")
    ports = NIListField(type_args=(lambda: Port,), rel_name='Connected_to', \
        rel_method='_outgoing')

    class NIMetaType:
        ni_type = 'Cable'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


## If the list of differing forms/types/fiels grows we should use a cleaner way
if sunet_forms_enabled():
    class Cable(NIObjectType, PhysicalMixin):
        name = NIStringField(type_kwargs={ 'required': True })
        cable_type = NIChoiceField(dropdown_name="cable_types")
        description = NIStringField()
        provider = NISingleRelationField(field_type=(lambda: Provider), \
            rel_name="Provides", rel_method="_incoming")
        ports = NIListField(type_args=(lambda: Port,), \
            rel_name='Connected_to', rel_method='_outgoing')
        tele2_cable_contract = NIChoiceField(\
                                dropdown_name="tele2_cable_contracts")
        tele2_alternative_circuit_id = NIStringField()

        class NIMetaType:
            ni_type = 'Cable'
            ni_metatype = NIMETA_PHYSICAL
            context_method = sriutils.get_network_context


allowed_types_converthost = ['firewall', 'switch', 'pdu', 'router']


class Host(NIObjectType, PhysicalLogicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    host_type = graphene.String()
    operational_state = NIChoiceField(dropdown_name="operational_states", \
        type_kwargs={ 'required': True })
    ip_addresses = NIIPAddrField()
    responsible_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Takes_responsibility", rel_method="_incoming",
        check_permissions=False)
    support_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Supports", rel_method="_incoming", check_permissions=False)
    managed_by = NIChoiceField(dropdown_name="host_management_sw")
    backup = NIStringField()
    os = NIStringField()
    os_version = NIStringField()
    contract_number = NIStringField()
    rack_units = NIIntField() # Equipment height
    rack_position = NIIntField()
    rack_back = NIBooleanField()
    host_owner = NISingleRelationField(field_type=(lambda: Relation), rel_name="Owns", rel_method="_incoming")
    host_user = NISingleRelationField(field_type=(lambda: HostUser), rel_name="Uses", rel_method="_incoming")
    host_services = NIStringField()
    services_locked = NIBooleanField()
    services_checked = NIBooleanField()
    ports = NIListField(type_args=(lambda: Port,), rel_name='Has',
        rel_method='_outgoing')
    location = graphene.Field(lambda:Location)

    def resolve_location(self, info, **kwargs):
        return PhysicalMixin.resolve_location(self, info, **kwargs)

    def resolve_host_type(self, info, **kwargs):
        '''Manual resolver for host type string'''
        return self.get_node().meta_type

    class NIMetaType:
        ni_type = 'Host'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_network_context


class Router(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    operational_state = NIChoiceField(dropdown_name="operational_states", \
        type_kwargs={ 'required': True })
    model = NIStringField()
    version = NIStringField()
    rack_units = NIIntField() # Equipment height
    rack_position = NIIntField()
    rack_back = NIBooleanField()
    ports = NIListField(type_args=(lambda: Port,), rel_name='Has',
        rel_method='_outgoing')

    class NIMetaType:
        ni_type = 'Router'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context
        can_create = False


class SwitchType(DjangoObjectType):
    '''
    This class represents a SwitchType for switch's mutations
    '''
    class Meta:
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
    operational_state = NIChoiceField(dropdown_name="operational_states", \
        type_kwargs={ 'required': True })
    ip_addresses = NIIPAddrField()
    responsible_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Takes_responsibility", rel_method="_incoming",
        check_permissions=False)
    support_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Supports", rel_method="_incoming", check_permissions=False)
    managed_by = NIChoiceField(dropdown_name="host_management_sw")
    backup = NIStringField()
    os = NIStringField()
    os_version = NIStringField()
    contract_number = NIStringField()
    rack_units = NIIntField() # Equipment height
    rack_position = NIIntField()
    rack_back = NIBooleanField()
    provider = NISingleRelationField(field_type=(lambda: Provider),
        rel_name="Provides", rel_method="_incoming")
    max_number_of_ports = NIIntField()
    ports = NIListField(type_args=(lambda: Port,), rel_name='Has',
                            rel_method='_outgoing')
    services_locked = NIBooleanField()
    services_checked = NIBooleanField()

    class NIMetaType:
        ni_type = 'Switch'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class Firewall(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    operational_state = NIChoiceField(dropdown_name="operational_states", \
        type_kwargs={ 'required': True })
    ip_addresses = NIIPAddrField()
    responsible_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Takes_responsibility", rel_method="_incoming",
        check_permissions=False)
    support_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Supports", rel_method="_incoming", check_permissions=False)
    managed_by = NIChoiceField(dropdown_name="host_management_sw")
    managed_by = NIChoiceField(dropdown_name="host_management_sw")
    backup = NIStringField()
    security_class = NIChoiceField(dropdown_name="security_classes")
    security_comment = NIStringField()
    os = NIStringField()
    os_version = NIStringField()
    model = NIStringField()
    vendor = NIStringField()
    service_tag = NIStringField()
    end_support = NIStringField()
    contract_number = NIStringField()
    rack_units = NIIntField() # Equipment height
    rack_position = NIIntField()
    rack_back = NIBooleanField()
    max_number_of_ports = NIIntField()
    services_locked = NIBooleanField()
    services_checked = NIBooleanField()
    ports = NIListField(type_args=(lambda: Port,), rel_name='Has',
                            rel_method='_outgoing')

    class NIMetaType:
        ni_type = 'Firewall'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context
        can_create = False


class ExternalEquipment(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    ports = NIListField(type_args=(lambda: Port,), rel_name='Has', rel_method='_outgoing')
    rack_units = NIIntField() # Equipment height
    rack_position = NIIntField()
    rack_back = NIBooleanField()

    class NIMetaType:
        ni_type = 'External Equipment'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class OpticalNode(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    type = NIChoiceField(dropdown_name="optical_node_types", \
        type_kwargs={ 'required': True })
    ports = NIListField(type_args=(lambda: Port,), rel_name='Has', rel_method='_outgoing')
    rack_units = NIIntField()
    rack_position = NIIntField()
    rack_back = NIBooleanField()
    operational_state = NIChoiceField(dropdown_name="operational_states", \
        type_kwargs={ 'required': True })

    class NIMetaType:
        ni_type = 'Optical Node'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class ODF(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    operational_state = NIChoiceField(dropdown_name="operational_states", \
        type_kwargs={ 'required': False })
    rack_units = NIIntField() # Equipment height
    rack_position = NIIntField()
    rack_back = NIBooleanField()
    max_number_of_ports = NIIntField()
    ports = NIListField(type_args=(lambda: Port,), rel_name='Has', rel_method='_outgoing')

    class NIMetaType:
        ni_type = 'ODF'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


## Optical Nodes
class OpticalFilter(NIObjectType, PhysicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    operational_state = NIChoiceField(dropdown_name="operational_states", \
        type_kwargs={ 'required': False })
    rack_units = NIIntField() # Equipment height
    rack_position = NIIntField()
    rack_back = NIBooleanField()
    max_number_of_ports = NIIntField()
    ports = NIListField(type_args=(lambda: Port,), rel_name='Has', rel_method='_outgoing')

    class NIMetaType:
        ni_type = 'Optical Filter'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class OpticalLink(NIObjectType, LogicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    link_type = NIChoiceField(dropdown_name="optical_link_types", \
        type_kwargs={ 'required': False })
    interface_type = NIChoiceField(dropdown_name="optical_link_interface_type", \
        type_kwargs={ 'required': False })
    operational_state = NIChoiceField(dropdown_name="operational_states", \
        type_kwargs={ 'required': False })
    provider = NISingleRelationField(field_type=(lambda: Provider), rel_name="Provides", rel_method="_incoming")
    ports = NIListField(type_args=(lambda: Port,), rel_name='Depends_on', rel_method='get_dependencies')

    class NIMetaType:
        ni_type = 'Optical Link'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_network_context


class OpticalMultiplexSection(NIObjectType, LogicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    operational_state = NIChoiceField(dropdown_name="operational_states", \
        type_kwargs={ 'required': False })
    provider = NISingleRelationField(field_type=(lambda: Provider), rel_name="Provides", rel_method="_incoming")

    class NIMetaType:
        ni_type = 'Optical Multiplex Section'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_network_context


class OpticalPath(NIObjectType, LogicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    framing = NIChoiceField(dropdown_name="optical_path_framing", \
        type_kwargs={ 'required': False })
    capacity = NIChoiceField(dropdown_name="optical_path_capacity", \
        type_kwargs={ 'required': False })
    wavelength = NIIntField() # Equipment height
    operational_state = NIChoiceField(dropdown_name="operational_states", \
        type_kwargs={ 'required': False })
    enrs = NIJSONField()
    provider = NISingleRelationField(field_type=(lambda: Provider), rel_name="Provides", rel_method="_incoming")

    class NIMetaType:
        ni_type = 'Optical Path'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_network_context


## Locations
class Site(NIObjectType, LocationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    site_type = NIChoiceField(dropdown_name="site_types", \
        type_kwargs={ 'required': False })
    country = NIStringField()
    country_code = NIChoiceField(dropdown_name="countries", \
        type_kwargs={ 'required': False })
    area = NIStringField()
    longitude = NIFloatField()
    latitude = NIFloatField()
    site_responsible = NISingleRelationField(field_type=SiteOwner,\
        rel_name="Responsible_for", rel_method="_incoming")
    owner_id = NIStringField()
    owner_site_name = NIStringField()
    url = NIStringField()
    telenor_subscription_id = NIStringField()
    addresses = NIListField(type_args=(lambda: Address,),\
        rel_name='Has_address', rel_method='_outgoing')
    #rooms = NIListField(type_args=(lambda: Room,), rel_name='Has', rel_method='_outgoing')
    #equipments = NIListField(type_args=(lambda: Physical,), rel_name='Has', rel_method='_outgoing')

    class NIMetaType:
        ni_type = 'Site'
        ni_metatype = NIMETA_LOCATION
        context_method = sriutils.get_network_context


class Room(NIObjectType, LocationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    floor = NIStringField()

    class NIMetaType:
        ni_type = 'Room'
        ni_metatype = NIMETA_LOCATION
        context_method = sriutils.get_network_context


def front_back_filter(is_back=False):
    def filter_node(node):
        rack_back = node.data.get('rack_back', None)

        if rack_back != None:
            if rack_back == is_back:
                return node

    return filter_node

class Rack(NIObjectType, LocationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    height = NIIntField()
    depth = NIIntField()
    width = NIIntField()
    rack_units = NIIntField()
    front = NIListField(type_args=(lambda: PhysicalLogical,),\
        rel_name='Located_in', rel_method='get_located_in',\
        filter=front_back_filter(False))
    back  = NIListField(type_args=(lambda: PhysicalLogical,),\
        rel_name='Located_in', rel_method='get_located_in',\
        filter=front_back_filter(True))

    class NIMetaType:
        ni_type = 'Rack'
        ni_metatype = NIMETA_LOCATION
        context_method = sriutils.get_network_context


## Peering
class PeeringPartner(NIObjectType, RelationMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    as_number = NIStringField()
    peering_link = graphene.String()
    ip_address = graphene.String() # only for PeeringGroup's "used_by" list

    def resolve_peering_link(self, info, **kwargs):
        '''Manual resolver for the peering_link field'''
        as_number = self.get_node().data.get('as_number', None)

        return 'https://www.peeringdb.com/asn/{}'.format(as_number)

    def resolve_ip_address(self, info, **kwargs):
        '''Manual resolver for the ip field'''
        ret = None

        if hasattr(self, 'relation_id'):
            rel = nc.get_relationship_bundle(nc.graphdb.manager, self.relation_id)
            ret = rel['data'].get('ip_address', None)

        return ret

    class NIMetaType:
        ni_type = 'Peering Partner'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


class PeeringGroup(NIObjectType, LogicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    ip_address = graphene.String() # only for PeeringPartner's "uses" list

    def resolve_ip_address(self, info, **kwargs):
        '''Manual resolver for the ip field'''
        ret = None

        if hasattr(self, 'relation_id'):
            rel = nc.get_relationship_bundle(nc.graphdb.manager, self.relation_id)
            ret = rel['data'].get('ip_address', None)

        return ret

    class NIMetaType:
        ni_type = 'Peering Group'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_network_context
        can_create = False


# Service
class ServiceClassFilter(graphene.InputObjectType):
    id = graphene.ID()
    name_contains = graphene.String()


class ServiceClassOrder(graphene.Enum):
    name_ASC = 'name_ASC'
    name_DESC = 'name_DESC'


def resolve_service_classes_connection(self, info, **kwargs):
    ret = None

    if info.context and info.context.user.is_authenticated:
        ret = ServiceClassModel.objects.all()

        # get filter
        filter = kwargs.get('filter', {})

        if filter:
            if filter.get('name_contains', None):
                # filter by name
                name_contains = filter.get('name_contains', None)
                ret = ret.filter(name__icontains=name_contains)
            elif filter.get('id', None):
                # filter by id
                id = filter.get('id', None)
                django_id = None

                try:
                    _type, django_id = relay.Node.from_global_id(id)
                except:
                    # we'll return None
                    django_id = None

                if django_id:
                    ret = ret.filter(id=django_id)

        # get order
        orderBy = kwargs.get('orderBy', None)

        if orderBy:
            order = orderBy.split('_')[1]
            if order == 'ASC':
                ret = ret.order_by('-name')
            elif order == 'DESC':
                ret = ret.order_by('name')

    else:
        raise GraphQLAuthException()

    return ret


class ServiceClass(DjangoObjectType):
    '''
    This class represents a ServiceType for service's mutations
    '''

    @classmethod
    def get_connection_class(cls):
        class_name = '{}Connection'.format(cls)
        meta_class = type('Meta', (object,), dict(node=cls))
        the_class = type(class_name, (graphene.relay.Connection, ),
                            dict(Meta=meta_class))

        return the_class

    class Meta:
        model = ServiceClassModel
        interfaces = (graphene.relay.Node, )


class ServiceType(DjangoObjectType):
    '''
    This class represents a ServiceType for service's mutations
    '''
    class Meta:
        model = ServiceTypeModel
        interfaces = (graphene.relay.Node, )


def resolve_getServiceTypes(self, info, **kwargs):
    if info.context and info.context.user.is_authenticated:
        return ServiceTypeModel.objects.all()
    else:
        raise GraphQLAuthException()


class Service(NIObjectType, LogicalMixin):
    name = NIStringField(type_kwargs={ 'required': True })
    description = NIStringField()
    service_type = graphene.Field(ServiceType)
    service_class = graphene.Field(ServiceClass)
    operational_state = NIChoiceField(dropdown_name="operational_states")
    responsible_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Takes_responsibility", rel_method="_incoming",
        check_permissions=False)
    support_group = NISingleRelationField(field_type=(lambda: Group),
        rel_name="Supports", rel_method="_incoming", check_permissions=False)
    project_end_date = NIDateField()
    decommissioned_date = NIDateField()
    ncs_service_name = NIStringField()
    vpn_type = NIStringField()
    vlan = NIStringField()
    vrf_target = NIStringField()
    route_distinguisher = NIStringField()
    contract_number = NIStringField()
    customers = NIListField(type_args=(lambda: Customer,), rel_name='Uses',
        rel_method='_incoming')
    end_users = NIListField(type_args=(lambda: EndUser,), rel_name='Uses',
        rel_method='_incoming')

    def resolve_service_class(self, info, **kwargs):
        ret = None
        service_class_name = self.get_node().data.get("service_class")

        if service_class_name:
            ret = ServiceClassModel.objects.get(name=service_class_name)

        return ret

    def resolve_service_type(self, info, **kwargs):
        ret = None
        service_type_name = self.get_node().data.get("service_type")

        if service_type_name:
            ret = ServiceTypeModel.objects.get(name=service_type_name)

        return ret

    class NIMetaType:
        ni_type = 'Service'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_network_context
        manual_filter_fields = {
            "service_type": graphene.types.scalars.String,
            "service_class": graphene.types.scalars.String,
        }


network_type_resolver = {
    # Organizations
    'Customer': Customer,
    'End User': EndUser,
    'Provider': Provider,
    'Site Owner': SiteOwner,

    # Equipment and cables
    'Port': Port,
    'Cable': Cable,
    'Host': Host,
    'Host User': HostUser,
    'Switch': Switch,
    'Unit': Unit,
    'Router': Router,
    'Firewall': Firewall,
    'External Equipment': ExternalEquipment,
    'Optical Node': OpticalNode,
    'ODF': ODF,

    # Optical Nodes
    'Optical Filter': OpticalFilter,
    'Optical Link': OpticalLink,
    'Optical Multiplex Section': OpticalMultiplexSection,
    'Optical Path': OpticalPath,

    # Peering
    'Peering Partner': PeeringPartner,
    'Peering Group': PeeringGroup,

    # Location
    'Site': Site,
    'Room': Room,
    'Rack': Rack,

    # Service
    'Service': Service,
}
