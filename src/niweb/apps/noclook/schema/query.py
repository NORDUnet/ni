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

            node_type     = NodeType.objects.filter(type=ni_type).first() if can_load_models() else None

            if node_type:
                type_name     = node_type.type
                type_slug     = node_type.slug

                # add simple list attribute and resolver
                field_name    = 'all_{}s'.format(type_slug)
                resolver_name = 'resolve_{}'.format(field_name)

                setattr(cls, field_name, graphene.List(graphql_type))
                setattr(cls, resolver_name, graphql_type.get_list_resolver())

                # add simple counter
                field_name    = 'count_{}s'.format(type_slug)
                resolver_name = 'resolve_{}'.format(field_name)

                setattr(cls, field_name, graphene.Int())
                setattr(cls, resolver_name, graphql_type.get_count_resolver())

                # add connection attribute
                field_name    = '{}s'.format(type_slug)
                resolver_name = 'resolve_{}'.format(field_name)

                connection_input, connection_order = graphql_type.build_filter_and_order()
                connection_meta = type('Meta', (object, ), dict(node=graphql_type))
                connection_class = type(
                    '{}Connection'.format(graphql_type.__name__),
                    (graphene.relay.Connection,),
                    #(connection_type,),
                    dict(Meta=connection_meta)
                )

                setattr(cls, field_name, graphene.relay.ConnectionField(
                    connection_class,
                    filter=graphene.Argument(connection_input),
                    orderBy=graphene.Argument(connection_order),
                ))
                setattr(cls, resolver_name, graphql_type.get_connection_resolver())

                ## build field and resolver byid
                field_name    = 'get{}ById'.format(type_name)
                resolver_name = 'resolve_{}'.format(field_name)

                setattr(cls, field_name, graphene.Field(graphql_type, id=graphene.ID()))
                setattr(cls, resolver_name, graphql_type.get_byid_resolver())


class NOCRootQuery(NOCAutoQuery):
    getAvailableDropdowns = graphene.List(graphene.String)
    getChoicesForDropdown = graphene.List(Choice, name=graphene.String(required=True))
    roles = relay.ConnectionField(RoleConnection, filter=graphene.Argument(RoleFilter), orderBy=graphene.Argument(RoleOrderBy))
    checkExistentOrganizationId = graphene.Boolean(organization_id=graphene.String(required=True), handle_id=graphene.Int())

    # get roles lookup
    getAvailableRoleGroups = graphene.List(RoleGroup)
    getRolesFromRoleGroup = graphene.List(Role, name=graphene.String())

    def resolve_getAvailableDropdowns(self, info, **kwargs):
        django_dropdowns = [d.name for d in DropdownModel.objects.all()]

        return django_dropdowns

    def resolve_getChoicesForDropdown(self, info, **kwargs):
        # django dropdown resolver
        name = kwargs.get('name')
        ddqs = DropdownModel.get(name)

        if not isinstance(ddqs, DummyDropdown):
            return ddqs.choice_set.order_by('name')
        else:
            raise Exception(u'Could not find dropdown with name \'{}\'. Please create it using /admin/'.format(name))

    def resolve_roles(self, info, **kwargs):
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
            if filter.handle_id:
                qs = qs.filter(handle_id=filter.handle_id)

            if filter.name:
                qs = qs.filter(name=filter.name)

        return qs

    def resolve_getAvailableRoleGroups(self, info, **kwargs):
        ret = []

        if info.context and info.context.user.is_authenticated:
            # well use the community context to check if the user
            # can read the rolegroup list
            community_context = sriutils.get_community_context()
            authorized = sriutils.authorize_list_module(
                info.context.user, community_context
            )

            if not authorized:
                raise GraphQLAuthException()

            ret = RoleGroupModel.objects.all()
        else:
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

            if not authorized:
                raise GraphQLAuthException()

            role_group = RoleGroupModel.objects.get(name=name)
            ret = RoleModel.objects.filter(role_group=role_group)
        else:
            raise GraphQLAuthException()

        return ret

    def resolve_checkExistentOrganizationId(self, info, **kwargs):
        # django dropdown resolver
        organization_id = kwargs.get('organization_id')
        handle_id = kwargs.get('handle_id', None)

        ret = nc.models.OrganizationModel.check_existent_organization_id(organization_id, handle_id, nc.graphdb.manager)

        return ret

    class NIMeta:
        graphql_types = [ Group, Address, Phone, Email, Contact, Organization, Procedure, Host ]
