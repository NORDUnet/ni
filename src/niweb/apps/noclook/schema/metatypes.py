# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle
import graphene

## metatype interfaces
class NINode(graphene.Node):
    name = graphene.String(required= True)


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
    pass


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
    pass
