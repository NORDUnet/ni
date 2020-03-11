# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle
import graphene
import logging
import importlib

logger = logging.getLogger(__name__)

## metatype interfaces
class NINode(graphene.Node):
    handle_id = graphene.Int(required=True)
    name = graphene.String(required= True)

    @classmethod
    def resolve_type(cls, instance, info):
        mod_types = importlib.import_module('apps.noclook.schema.types')
        community_type_resolver = getattr(mod_types, 'community_type_resolver')
        network_type_resolver = getattr(mod_types, 'network_type_resolver')

        type_name = instance.node_type.type

        if type_name in community_type_resolver.keys():
            return community_type_resolver[type_name]
        elif type_name in network_type_resolver.keys():
            return network_type_resolver[type_name]
        else:
            super().resolve_type(instance, info)


class Logical(NINode):
    part_of = graphene.Field(lambda:Physical)


class Relation(NINode):
    name = graphene.String(required= True)
    with_same_name = graphene.List(lambda:Relation)
    uses = graphene.Field(Logical)
    provides = graphene.Field(NINode) # Physical or Logical
    owns = graphene.Field(lambda:Physical)
    responsible_for = graphene.Field(lambda:Location)


class Physical(NINode):
    location = graphene.Field(lambda:Location)
    has = graphene.Field(lambda:Physical)
    part_of = graphene.Field(lambda:Logical)
    parent = graphene.Field(lambda:Physical)


class Location(NINode):
    parent = graphene.Field(lambda:Location)
    located_in = graphene.Field(lambda:Physical)
    has = graphene.Field(lambda:Physical)


## metatype resolver mixins
class ResolverUtils:
    @staticmethod
    def single_relation_resolver(info, node, method_name, relation_label):
        ret = None

        if info.context and info.context.user.is_authenticated:
            method = getattr(node, method_name)
            relation = method()

            if relation.get(relation_label):
                handle_id = relation[relation_label][0]['node'].handle_id

                if handle_id and \
                    NodeHandle.objects.filter(handle_id=handle_id):

                    ret = NodeHandle.objects.get(handle_id=handle_id)

        return ret

class LogicalMixin:
    def resolve_part_of(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_part_of', 'Part_of')


class RelationMixin:
    def resolve_with_same_name(self, info, **kwargs):
        ret = None

        # check permission?
        if info.context and info.context.user.is_authenticated:
            ids_samename = self.get_node().with_same_name().get('ids', None)
            if ids_samename and len(ids_samename) > 0:
                ret = NodeHandle.objects.filter(handle_id__in=ids_samename)

        return ret

    def resolve_uses(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_uses', 'Uses')

    def resolve_provides(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_provides', 'Provides')

    def resolve_owns(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_owns', 'Owns')

    def resolve_responsible_for(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_responsible_for', 'Responsible_for')


class PhysicalMixin:
    def resolve_location(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_location', 'Located_in')

    def resolve_has(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_has', 'Has')

    def resolve_part_of(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_part_of', 'Part_of')

    def resolve_parent(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_parent', 'Has')


class LocationMixin:
    def resolve_parent(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_parent', 'Has')

    def resolve_located_in(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_located_in', 'Located_in')

    def resolve_has(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_has', 'Has')
