# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc

from graphql import GraphQLError
from ..models import Dropdown as DropdownModel
from .types import *

class NOCRootQuery(NOCAutoQuery):
    getAvailableDropdowns = graphene.List(graphene.String)
    getChoicesForDropdown = graphene.List(KeyValue, name=graphene.String(required=True))
    getRelationById = graphene.Field(NIRelationType, relation_id=graphene.Int(required=True))
    getRoleRelationById = graphene.Field(RoleRelation, relation_id=graphene.Int(required=True))

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

        return rel

    def resolve_getRoleRelationById(self, info, **kwargs):
        relation_id = kwargs.get('relation_id')
        rel = nc.models.RoleRelationship.get_relationship_model(nc.graphdb.manager, relationship_id=relation_id)
        rel.relation_id = rel.id

        return rel

    class NIMeta:
        graphql_types = [ Group, Contact, Organization, Procedure, Host ]
