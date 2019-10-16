# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc
import apps.noclook.vakt.utils as sriutils

from django.apps import apps
from graphql import GraphQLError
from ..models import Dropdown as DropdownModel, Role as RoleModel, DummyDropdown
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

def get_node2node_relations_resolver(id1_name, id2_name, rel_type):
    def resolve_getNode1Node2Relations(self, info, **kwargs):
        group_id = kwargs.get(id1_name)
        contact_id = kwargs.get(id2_name)

        authorized_node1 = sriutils.authorice_read_resource(
            info.context.user, group_id
        )

        authorized_node2 = sriutils.authorice_read_resource(
            info.context.user, contact_id
        )

        if not (authorized_node1 and authorized_node2):
            raise GraphQLAuthException()

        relationships = nc.get_relationships(nc.graphdb.manager, handle_id1=group_id, handle_id2=contact_id, rel_type=rel_type)

        output = []
        for relationship in relationships:
            rel = nc.get_relationship_model(nc.graphdb.manager, relationship_id=relationship._id)
            rel.relation_id = rel.id
            output.append(rel)

        return output

    return resolve_getNode1Node2Relations


resolve_getGroupContactRelations = get_node2node_relations_resolver('group_id', 'contact_id',  'Member_of')
resolve_getContactEmailRelations = get_node2node_relations_resolver('contact_id', 'email_id',  'Has_email')
resolve_getContactPhoneRelations = get_node2node_relations_resolver('contact_id', 'phone_id',  'Has_phone')
resolve_getOrganizationAddressRelations = get_node2node_relations_resolver('organization_id', 'address_id',  'Has_address')


class NOCRootQuery(NOCAutoQuery):
    getAvailableDropdowns = graphene.List(graphene.String)
    getChoicesForDropdown = graphene.List(Choice, name=graphene.String(required=True))
    getRelationById = graphene.Field(NIRelationType, relation_id=graphene.Int(required=True))
    getRoleRelationById = graphene.Field(RoleRelation, relation_id=graphene.Int(required=True))
    roles = relay.ConnectionField(RoleConnection, filter=graphene.Argument(RoleFilter), orderBy=graphene.Argument(RoleOrderBy))
    getOrganizationContacts = graphene.List(ContactWithRolename, handle_id=graphene.Int(required=True))
    getGroupContacts = graphene.List(ContactWithRelation, handle_id=graphene.Int(required=True))

    # relationship lookups
    getGroupContactRelations = graphene.List(NIRelationType, group_id=graphene.Int(required=True), contact_id=graphene.Int(required=True), resolver=resolve_getGroupContactRelations)
    getContactEmailRelations = graphene.List(NIRelationType, contact_id=graphene.Int(required=True), email_id=graphene.Int(required=True), resolver=resolve_getContactEmailRelations)
    getContactPhoneRelations = graphene.List(NIRelationType, contact_id=graphene.Int(required=True), phone_id=graphene.Int(required=True), resolver=resolve_getContactPhoneRelations)
    getOrganizationAddressRelations = graphene.List(NIRelationType, organization_id=graphene.Int(required=True), address_id=graphene.Int(required=True), resolver=resolve_getOrganizationAddressRelations)

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

    def resolve_getOrganizationContacts(self, info, **kwargs):
        ret = []

        handle_id = kwargs.get('handle_id')

        # check read permissions
        authorized = sriutils.authorice_read_resource(
            info.context.user, handle_id
        )

        if not authorized:
            raise GraphQLAuthException()

        organization_nh = NodeHandle.objects.get(handle_id=handle_id)
        relations = organization_nh.get_node().get_relations()['Works_for']

        for relation in relations:
            # resolve contact
            contact_node = relation['node']
            contact_id = contact_node.handle_id
            contact_nh = NodeHandle.objects.get(handle_id=contact_id)

            # resolve role object
            relationship = relation['relationship']
            relation_id = relation['relationship_id']
            role_name = relation['relationship']._properties['name']
            role_obj = RoleModel.objects.get(name=role_name)

            contact_wrn = {
                'contact': contact_nh,
                'role': role_obj,
                'relation_id': relation_id,
            }

            ret.append(contact_wrn)

        return ret

    def resolve_getGroupContacts(self, info, **kwargs):
        ret = []

        handle_id = kwargs.get('handle_id')

        # check read permissions
        authorized = sriutils.authorice_read_resource(
            info.context.user, handle_id
        )

        if not authorized:
            raise GraphQLAuthException()

        group_nh = NodeHandle.objects.get(handle_id=handle_id)
        relations = group_nh.get_node().get_relations()['Member_of']

        for relation in relations:
            # resolve contact
            contact_node = relation['node']
            contact_id = contact_node.handle_id
            contact_nh = NodeHandle.objects.get(handle_id=contact_id)

            # resolve role object
            relationship_id = relation['relationship_id']

            contact_wrn = {
                'contact': contact_nh,
                'relation_id': relationship_id,
            }

            ret.append(contact_wrn)

        return ret

    class NIMeta:
        graphql_types = [ Group, Address, Phone, Email, Contact, Organization, Procedure, Host ]
