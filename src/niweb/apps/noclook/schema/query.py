# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc
import apps.noclook.vakt.utils as sriutils

from django.apps import apps
from graphql import GraphQLError
from ..models import Dropdown as DropdownModel, Role as RoleModel, DummyDropdown,\
                RoleGroup as RoleGroupModel, DEFAULT_ROLEGROUP_NAME
from .types import *
from .search import *

def can_load_models():
    can_load = True

    try:
        NodeType.objects.all().first()
    except:
        can_load = False

    return can_load


class NOCAutoQuery(graphene.ObjectType):
    '''
    This class creates a connection and a getById method for each of the types
    declared on the graphql_types of the NIMeta class of any subclass.
    '''

    connection_classes = {}

    # the key for these dicts is noclook's NodeType model
    by_id_type_resolvers = {}
    all_type_resolvers = {}
    connection_type_resolvers = {}

    # the key for these is graphene types instead for fast search
    graph_by_id_type_resolvers = {}
    graph_all_type_resolvers = {}
    graph_connection_type_resolvers = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        _nimeta = getattr(cls, 'NIMeta')
        graphql_types = getattr(_nimeta, 'graphql_types')

        # add list with pagination resolver
        # add by id resolver
        for graphql_type in graphql_types:
            ## extract values
            ni_type = graphql_type.get_from_nimetatype('ni_type')
            assert ni_type, '{} has not set its ni_type attribute'.format(cls.__name__)
            ni_metatype = graphql_type.get_from_nimetatype('ni_metatype')
            assert ni_metatype, '{} has not set its ni_metatype attribute'.format(cls.__name__)

            sluggy = slugify(ni_type)
            node_type = NodeType.objects.get_or_create(type=ni_type, slug=sluggy)[0] if can_load_models() else None

            if node_type:
                type_name = node_type.type
                type_slug = node_type.slug

                # relace - in slug for _
                fmt_type_slug = type_slug.replace('-', '')
                fmt_type_name = type_name.replace(' ', '')
                components = type_name.split(' ')
                # type name camelcased
                type_name_cc = components[0].lower() + ''.join(x.title() for x in components[1:])

                # add simple list attribute and resolver
                field_name    = 'all_{}s'.format(fmt_type_slug)
                resolver_name = 'resolve_{}'.format(field_name)

                # add resolvers
                cls.all_type_resolvers[node_type] = {
                    'field_name': field_name,
                    'fmt_type_name': fmt_type_name,
                }

                cls.graph_all_type_resolvers[graphql_type] = {
                    'field_name': field_name,
                    'fmt_type_name': fmt_type_name,
                }

                setattr(cls, field_name, graphene.List(graphql_type))
                setattr(cls, resolver_name, graphql_type.get_list_resolver())

                # add connection attribute
                field_name    = '{}s'.format(type_name_cc)
                resolver_name = 'resolve_{}'.format(field_name)

                # add resolvers
                cls.connection_type_resolvers[node_type] = {
                    'field_name': field_name,
                    'fmt_type_name': fmt_type_name,
                }

                cls.graph_connection_type_resolvers[graphql_type] = {
                    'field_name': field_name,
                    'fmt_type_name': fmt_type_name,
                }

                connection_input, connection_order = graphql_type.build_filter_and_order()
                connection_meta = type('Meta', (object, ), dict(node=graphql_type))
                connection_name = '{}Connection'.format(type_name_cc)
                connection_class = None

                if connection_name not in cls.connection_classes:
                    connection_class = type(
                        connection_name,
                        (graphene.relay.Connection,),
                        #(connection_type,),
                        dict(Meta=connection_meta)
                    )
                    cls.connection_classes[connection_name] = connection_class
                else:
                    connection_class = cls.connection_classes[connection_name]

                setattr(cls, field_name, graphene.relay.ConnectionField(
                    connection_class,
                    filter=graphene.Argument(connection_input),
                    orderBy=graphene.Argument(connection_order),
                ))
                setattr(cls, resolver_name, graphql_type.get_connection_resolver())

                ## build field and resolver byid
                field_name    = 'get{}ById'.format(fmt_type_name)
                resolver_name = 'resolve_{}'.format(field_name)

                # add resolvers
                cls.by_id_type_resolvers[node_type] = {
                    'field_name': field_name,
                    'fmt_type_name': fmt_type_name,
                }

                cls.graph_by_id_type_resolvers[graphql_type] = {
                    'field_name': field_name,
                    'fmt_type_name': fmt_type_name,
                }

                setattr(cls, field_name, graphene.Field(graphql_type, id=graphene.ID()))
                setattr(cls, resolver_name, graphql_type.get_byid_resolver())

        ## add search queries
        search_queries = getattr(_nimeta, 'search_queries')

        for search_query in search_queries:
            field_resolver = search_query.get_query_field_resolver()
            # set field
            setattr(cls, field_resolver['field'][0], field_resolver['field'][1])

            # set resolver
            setattr(cls, field_resolver['resolver'][0], field_resolver['resolver'][1])

        ## add metatype connections
        metatypes = getattr(_nimeta, 'metatypes', [])

        for metatype in metatypes:
            connection_name = '{}s'.format(str(metatype).lower())
            connection_field = relay.ConnectionField(
                                    metatype.get_connection_class(),
                                    filter=graphene.Argument(MetatypeFilter),
                                    orderBy=graphene.Argument(MetatypeOrder),
                                    resolver=metatype.get_connection_resolver())

            setattr(cls, connection_name, connection_field)


def get_typelist_resolver(class_list):
    def resolve_class_list(self, info, **kwargs):
        if info.context and info.context.user.is_authenticated:
            classes = []

            for clazz in class_list:
                class_has_resolvers = \
                    clazz in NOCRootQuery.graph_by_id_type_resolvers and \
                    clazz in NOCRootQuery.graph_all_type_resolvers and \
                    clazz in NOCRootQuery.graph_connection_type_resolvers

                if class_has_resolvers:
                    byid_name = NOCRootQuery.\
                        graph_by_id_type_resolvers[clazz]['field_name']

                    connection_name = NOCRootQuery.\
                        graph_connection_type_resolvers[clazz]['field_name']

                    all_name = NOCRootQuery.\
                        graph_all_type_resolvers[clazz]['field_name']

                    can_create = clazz.can_create()

                    elem = TypeInfo(
                        type_name=clazz,
                        connection_name=connection_name,
                        byid_name=byid_name,
                        all_name=all_name,
                        can_create=can_create,
                    )

                    classes.append(elem)

            return classes
        else:
            raise GraphQLAuthException()

    return resolve_class_list


network_org_types = [Customer, EndUser, Provider, SiteOwner]
host_owner_types = [Customer, EndUser, Provider, HostUser]
optical_path_dependency_types = [
                                    ODF, OpticalLink, OpticalMultiplexSection,
                                    OpticalNode, Router, Switch, OpticalPath,
                                    Service,
                                ]
router_dependents_types = [
    Service, OpticalPath, OpticalMultiplexSection, OpticalLink
]


class NOCRootQuery(NOCAutoQuery):
    ninodes = relay.ConnectionField(NINode.get_connection_class(),
        filter=graphene.Argument(GenericNodeFilter),
        orderBy=graphene.Argument(GenericNodeOrder),
        resolver=NINode.get_connection_resolver())

    getAvailableDropdowns = graphene.List(graphene.String)
    getChoicesForDropdown = graphene.List(Choice, name=graphene.String(required=True))
    roles = relay.ConnectionField(RoleConnection, filter=graphene.Argument(RoleFilter), orderBy=graphene.Argument(RoleOrderBy))
    checkExistentOrganizationId = graphene.Boolean(organization_id=graphene.String(required=True), id=graphene.ID())

    # get roles lookup
    getAvailableRoleGroups = graphene.List(RoleGroup)
    getRolesFromRoleGroup = graphene.List(Role, name=graphene.String())

    # get metatypes lookup
    getMetatypes = graphene.List(MetaType)
    getTypesForMetatype = graphene.List(TypeInfo,
                            metatype=graphene.Argument(MetaType))

    # activity connection
    getAvailableContexts = graphene.List(graphene.String,
                            resolver=resolve_available_contexts)
    getContextActivity = relay.ConnectionField(
                            ActionConnection,
                            filter=graphene.Argument(ActionFilter,
                                                        required=True),
                            orderBy=graphene.Argument(ActionOrderBy),
                            resolver=resolve_context_activity)

    # switch types
    getSwitchTypes = graphene.List(SwitchType, resolver=resolve_getSwitchTypes)

    # network organizations
    getNetworkOrgTypes = graphene.List(TypeInfo,
        resolver=get_typelist_resolver(network_org_types))

    # convert host allowed slugs
    getAllowedTypesConvertHost = graphene.List(graphene.String)

    # physical host owner
    getHostOwnerTypes = graphene.List(TypeInfo,
            resolver=get_typelist_resolver(host_owner_types))

    # safe get groups for select combos
    getPlainGroups = graphene.List(PlainGroup)

    # optical_path_dependency_types
    getOpticalPathDependencyTypes = graphene.List(TypeInfo,
            resolver=get_typelist_resolver(optical_path_dependency_types))

    # router_dependents_types
    getRouterDependentsTypes = graphene.List(TypeInfo,
            resolver=get_typelist_resolver(router_dependents_types))

    # service types
    getServiceTypes = graphene.List(ServiceType, \
                        resolver=resolve_getServiceTypes)

    # user permissions
    getUserPermissions = graphene.Field(UserPermissions,
                            resolver=resolve_getUserPermissions)

    # users list and query
    getUserById = graphene.Field(User, ID=graphene.Argument(graphene.ID),
                    resolver=resolve_getUserById)
    users = relay.ConnectionField(UserConnection,
                filter=graphene.Argument(UserFilter),
                orderBy=graphene.Argument(UserOrder),
                resolver=resolve_users)

    services_classes = relay.ConnectionField(
        ServiceClass.get_connection_class(),
        filter=graphene.Argument(ServiceClassFilter),
        orderBy=graphene.Argument(ServiceClassOrder),
        resolver=resolve_service_classes_connection)


    def resolve_getPlainGroups(self, info, **kwargs):
        if info.context and info.context.user.is_authenticated:
            ret = []

            group_type_str = 'Group'
            group_type, created = NodeType.objects.get_or_create(
                type=group_type_str, slug=group_type_str.lower())

            groups = NodeHandle.objects.filter(node_type=group_type) \
                        .order_by('handle_id')

            for group in groups:
                id = relay.Node.to_global_id(group_type_str, \
                                                str(group.handle_id))
                name = group.node_name

                ret.append(PlainGroup(id=id, name=name))

            return ret
        else:
            raise GraphQLAuthException()


    def resolve_getAvailableDropdowns(self, info, **kwargs):
        if info.context and info.context.user.is_authenticated:
            django_dropdowns = [d.name for d in DropdownModel.objects.all()]

            return django_dropdowns
        else:
            raise GraphQLAuthException()


    def resolve_getChoicesForDropdown(self, info, **kwargs):
        if info.context and info.context.user.is_authenticated:
            # django dropdown resolver
            name = kwargs.get('name')
            ddqs = DropdownModel.get(name)

            if not isinstance(ddqs, DummyDropdown):
                return ddqs.choice_set.order_by('name')
            else:
                raise Exception(u'Could not find dropdown with name \'{}\'. Please create it using /admin/'.format(name))
        else:
            raise GraphQLAuthException()


    def resolve_roles(self, info, **kwargs):
        qs = RoleModel.objects.none()

        if info.context and info.context.user.is_authenticated:
            context = sriutils.get_community_context()
            authorized = sriutils.authorize_list_module(
                info.context.user, context
            )

            if authorized:
                filter = kwargs.get('filter')
                order_by = kwargs.get('orderBy')

                qs = RoleModel.objects.all()

                if order_by:
                    if order_by == RoleOrderBy.handle_id_ASC:
                        qs = qs.order_by('handle_id')
                    elif order_by == RoleOrderBy.handle_id_DESC:
                        qs = qs.order_by('-handle_id')
                    elif order_by == RoleOrderBy.name_ASC:
                        qs = qs.order_by('name')
                    elif order_by == RoleOrderBy.name_DESC:
                        qs = qs.order_by('-name')

                if filter:
                    if filter.id:
                        handle_id = relay.Node.from_global_id(filter.id)[1]
                        qs = qs.filter(handle_id=handle_id)

                    if filter.name:
                        qs = qs.filter(name=filter.name)

                return qs
            else:
                #403
                return qs
        else:
            # 401
            raise GraphQLAuthException()


    def resolve_getAvailableRoleGroups(self, info, **kwargs):
        ret = []

        if info.context and info.context.user.is_authenticated:
            # well use the community context to check if the user
            # can read the rolegroup list
            community_context = sriutils.get_community_context()
            authorized = sriutils.authorize_list_module(
                info.context.user, community_context
            )

            if authorized:
                ret = RoleGroupModel.objects.all()
        else:
            #401
            raise GraphQLAuthException()

        return ret


    def resolve_getRolesFromRoleGroup(self, info, **kwargs):
        ret = []
        name = kwargs.get('name', DEFAULT_ROLEGROUP_NAME)

        if info.context and info.context.user.is_authenticated:
            # well use the community context to check if the user
            # can read the rolegroup list
            community_context = sriutils.get_community_context()
            authorized = sriutils.authorize_list_module(
                info.context.user, community_context
            )

            if authorized:
                role_group = RoleGroupModel.objects.get(name=name)
                ret = RoleModel.objects.filter(role_group=role_group)
        else:
            #401
            raise GraphQLAuthException()

        return ret


    def resolve_checkExistentOrganizationId(self, info, **kwargs):
        ret = False

        if info.context and info.context.user.is_authenticated:
            # well use the community context to check if the user
            # can read the rolegroup list
            community_context = sriutils.get_community_context()
            authorized = sriutils.authorize_list_module(
                info.context.user, community_context
            )

            if authorized:
                id = kwargs.get('id', None)
                handle_id = None

                if id:
                    _type, handle_id = relay.Node.from_global_id(id)

                organization_id = kwargs.get('organization_id')

                ret = nc.models.OrganizationModel \
                        .check_existent_organization_id(
                            organization_id, handle_id, nc.graphdb.manager)
        else:
            raise GraphQLAuthException()

        return ret


    def resolve_getMetatypes(self, info, **kwargs):
        if info.context and info.context.user.is_authenticated:
            metatypes = [
                MetaType.Logical,
                MetaType.Relation,
                MetaType.Physical,
                MetaType.Location,
            ]

            return metatypes
        else:
            raise GraphQLAuthException()


    def resolve_getTypesForMetatype(self, info, **kwargs):
        if info.context and info.context.user.is_authenticated:
            classes = []
            filter_metatype = kwargs.get('metatype')

            for interface, class_list in subclasses_interfaces.items():
                if interface.__name__ == filter_metatype:
                    for clazz in class_list:
                        class_has_resolvers = \
                            clazz in NOCRootQuery.graph_by_id_type_resolvers and \
                            clazz in NOCRootQuery.graph_all_type_resolvers and \
                            clazz in NOCRootQuery.graph_connection_type_resolvers

                        if class_has_resolvers:
                            byid_name = NOCRootQuery.\
                                graph_by_id_type_resolvers[clazz]['field_name']

                            connection_name = NOCRootQuery.\
                                graph_connection_type_resolvers[clazz]['field_name']

                            all_name = NOCRootQuery.\
                                graph_all_type_resolvers[clazz]['field_name']

                            elem = TypeInfo(
                                type_name=clazz,
                                connection_name=connection_name,
                                byid_name=byid_name,
                                all_name=all_name,
                            )

                            classes.append(elem)

            return classes
        else:
            raise GraphQLAuthException()


    def resolve_getAllowedTypesConvertHost(self, info, **kwargs):
        if info.context and info.context.user.is_authenticated:
            return allowed_types_converthost
        else:
            raise GraphQLAuthException()


    class NIMeta:
        graphql_types = [
            # Community
            Group, Address, Phone, Email, Contact, Organization, Procedure,
            # Network
            ## Organizations
            Customer, EndUser, Provider, SiteOwner,
            ## Equipment and cables
            Port, Host, Cable, Router, Switch, Firewall, ExternalEquipment,
                OpticalNode, ODF, Unit,
            ## Optical Nodes
            OpticalFilter, OpticalLink, OpticalMultiplexSection, OpticalPath,
            ## Peering
            PeeringPartner, PeeringGroup,
            ## Locations
            Site, Room, Rack,
            ## Other
            HostUser,
            ## Service
            Service,
        ]

        search_queries = [
            GeneralSearchConnection,
            PortSearchConnection,
        ]

        metatypes = [
            PhysicalLogical, Logical, Physical, Relation, Location,
        ]
