# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle
import graphene

## metatype interfaces
class Logical(graphene.Interface):
    name = graphene.String(required= True)


class Relation(graphene.Interface):
    name = graphene.String(required= True)
    with_same_name = graphene.List(lambda:Relation)


class Physical(graphene.Interface):
    name = graphene.String(required= True)


class Location(graphene.Interface):
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


class PhysicalMixin:
    pass


class LocationMixin:
    pass
