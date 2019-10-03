# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc
import apps.noclook.vakt.utils as sriutils

from graphql import GraphQLError
from ..models import Dropdown as DropdownModel, Role as RoleModel, DummyDropdown
from .types import *

class NOCAutoQuery(graphene.ObjectType):
    '''
    This class creates a connection and a getById method for each of the types
    declared on the graphql_types of the NIMeta class of any subclass.
    '''
    node = relay.Node.Field()
    getNodeById = graphene.Field(NodeHandler, handle_id=graphene.Int())

    def resolve_getNodeById(self, info, **args):
        handle_id = args.get('handle_id')

        ret = None

        if info.context and info.context.user.is_authenticated:
            if handle_id:
                ret = NodeHandle.objects.get(handle_id=handle_id)
            else:
                raise GraphQLError('A valid handle_id must be provided')

            if not ret:
                raise GraphQLError("There isn't any {} with handle_id {}".format(nodetype, handle_id))

            return ret
        else:
            raise GraphQLAuthException()


    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        _nimeta = getattr(cls, 'NIMeta')
        graphql_types = getattr(_nimeta, 'graphql_types')

        assert graphql_types, \
            'A tuple with the types should be set in the Meta class of {}'.format(cls.__name__)

        # add list with pagination resolver
        # add by id resolver
        for graphql_type in graphql_types:
            ## extract values
            ni_type = graphql_type.get_from_nimetatype('ni_type')
            assert ni_type, '{} has not set its ni_type attribute'.format(cls.__name__)
            ni_metatype = graphql_type.get_from_nimetatype('ni_metatype')
            assert ni_metatype, '{} has not set its ni_metatype attribute'.format(cls.__name__)

            node_type     = NodeType.objects.filter(type=ni_type).first()

            if node_type:
                type_name     = node_type.type
                type_slug     = node_type.slug

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

                setattr(cls, field_name, graphene.Field(graphql_type, handle_id=graphene.Int()))
                setattr(cls, resolver_name, graphql_type.get_byid_resolver())

class NOCRootQuery(NOCAutoQuery):
    getAvailableDropdowns = graphene.List(graphene.String)
    getChoicesForDropdown = graphene.List(Choice, name=graphene.String(required=True))
    getRelationById = graphene.Field(NIRelationType, relation_id=graphene.Int(required=True))
    getRoleRelationById = graphene.Field(RoleRelation, relation_id=graphene.Int(required=True))
    roles = relay.ConnectionField(RoleConnection, filter=graphene.Argument(RoleFilter), orderBy=graphene.Argument(RoleOrderBy))

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

    def resolve_getRelationById(self, info, **kwargs):
        relation_id = kwargs.get('relation_id')
        rel = nc.get_relationship_model(nc.graphdb.manager, relationship_id=relation_id)
        rel.relation_id = rel.id

        start_id = rel.start['handle_id']
        end_id = rel.end['handle_id']

        authorized_start = sriutils.authorice_read_resource(
            info.context.user, start_id
        )

        authorized_end = sriutils.authorice_read_resource(
            info.context.user, end_id
        )

        if not (authorized_start and authorized_end):
            raise GraphQLAuthException()

        return rel

    def resolve_getRoleRelationById(self, info, **kwargs):
        relation_id = kwargs.get('relation_id')
        rel = nc.models.RoleRelationship.get_relationship_model(nc.graphdb.manager, relationship_id=relation_id)
        rel.relation_id = rel.id

        start_id = rel.start['handle_id']
        end_id = rel.end['handle_id']

        authorized_start = sriutils.authorice_read_resource(
            info.context.user, start_id
        )

        authorized_end = sriutils.authorice_read_resource(
            info.context.user, end_id
        )

        if not (authorized_start and authorized_end):
            raise GraphQLAuthException()

        return rel

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

    class NIMeta:
        graphql_types = [ Group, Contact, Organization, Procedure, Host ]
