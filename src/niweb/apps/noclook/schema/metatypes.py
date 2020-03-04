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


class Physical(graphene.Node):
    name = graphene.String(required= True)


class Location(graphene.Node):
    name = graphene.String(required= True)


## metatype resolver mixins
class LogicalMixin:
    pass


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
        ret = None

        if info.context and info.context.user.is_authenticated:
            uses = self.get_node().get_uses()
            if uses.get('Uses'):
                uses_handle_id = uses['Uses'][0]['node'].handle_id

                # check permission?
                if uses_handle_id and \
                    NodeHandle.objects.filter(handle_id=uses_handle_id):
                    pass
                    ret = NodeHandle.objects.get(handle_id=uses_handle_id)

        return ret


class PhysicalMixin:
    pass


class LocationMixin:
    pass
