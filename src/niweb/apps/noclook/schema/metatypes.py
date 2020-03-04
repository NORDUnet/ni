# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle
import graphene

## metatype interfaces
class Logical(graphene.Node):
    name = graphene.String(required= True)


class Relation(graphene.Node):
    name = graphene.String(required= True)
    with_same_name = graphene.List(lambda:Relation)
    uses = graphene.Field(Logical)
    provides = graphene.Field(graphene.Node)
    owns = graphene.Field(lambda:Physical)
    responsible_for = graphene.Field(lambda:Location)


class Physical(graphene.Node):
    name = graphene.String(required= True)


class Location(graphene.Node):
    name = graphene.String(required= True)


## metatype resolver mixins
class LogicalMixin:
    pass


class RelationMixin:
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

    def resolve_with_same_name(self, info, **kwargs):
        ret = None

        # check permission?
        if info.context and info.context.user.is_authenticated:
            ids_samename = self.get_node().with_same_name().get('ids', None)
            if ids_samename and len(ids_samename) > 0:
                ret = NodeHandle.objects.filter(handle_id__in=ids_samename)

        return ret

    def resolve_uses(self, info, **kwargs):
        return RelationMixin.single_relation_resolver(
            info, self.get_node(), 'get_uses', 'Uses')

    def resolve_provides(self, info, **kwargs):
        return RelationMixin.single_relation_resolver(
            info, self.get_node(), 'get_provides', 'Provides')

    def resolve_owns(self, info, **kwargs):
        return RelationMixin.single_relation_resolver(
            info, self.get_node(), 'get_owns', 'Owns')

    def resolve_responsible_for(self, info, **kwargs):
        return RelationMixin.single_relation_resolver(
            info, self.get_node(), 'get_responsible_for', 'Responsible_for')


class PhysicalMixin:
    pass


class LocationMixin:
    pass
