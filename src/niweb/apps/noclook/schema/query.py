# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc

from graphql import GraphQLError
from ..models import Dropdown as DropdownModel
from .types import *

def get_roles_dropdown():
    ret = []
    roles = nc.models.RoleRelationship.get_all_roles()
    for role in roles:
        name = role.replace(' ', '_').lower()
        ret.append(Neo4jChoice(name=name, value=role))

    return ret

NEO4J_DROPDOWNS = {
    'roles': get_roles_dropdown,
}

class NOCRootQuery(NOCAutoQuery):
    getAvailableDropdowns = graphene.List(graphene.String)
    getChoicesForDropdown = graphene.List(KeyValue, name=graphene.String(required=True))
    getRelationById = graphene.Field(NIRelationType, relation_id=graphene.Int(required=True))
    getRoleById = graphene.Field(Role, relation_id=graphene.Int(required=True))

    def resolve_getAvailableDropdowns(self, info, **kwargs):
        django_dropdowns = [d.name for d in DropdownModel.objects.all()]
        neo4j_dropdowns  = [x for x in NEO4J_DROPDOWNS.keys()]

        return django_dropdowns + neo4j_dropdowns

    def resolve_getChoicesForDropdown(self, info, **kwargs):
        name = kwargs.get('name')

        if name in NEO4J_DROPDOWNS.keys():
            # neo4j resolver
            dd_function = NEO4J_DROPDOWNS.get(name)

            if callable(dd_function):
                ret = dd_function()
                return ret
            else:
                raise Exception('Can\'t resolve {}'.format(name))
        else:
            # django dropdown resolver
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

    def resolve_getRoleById(self, info, **kwargs):
        relation_id = kwargs.get('relation_id')
        rel = nc.models.RoleRelationship.get_relationship_model(nc.graphdb.manager, relationship_id=relation_id)
        rel.relation_id = rel.id

        return rel

    class NIMeta:
        graphql_types = [ Group, Contact, Organization, Procedure, Host ]
