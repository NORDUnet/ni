# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook import helpers
from apps.noclook.models import NodeHandle, NodeType
from apps.noclook.vakt import utils as sriutils
from django.db.models import Q

import graphene
import logging
import importlib
import norduniclient as nc

logger = logging.getLogger(__name__)


class MetatypeFilter(graphene.InputObjectType):
    name_contains = graphene.String()
    type_in = graphene.List(graphene.String)


class MetatypeOrder(graphene.Enum):
    name_ASC = 'name_ASC'
    name_DESC = 'name_DESC'


## metatype interfaces
class NINode(graphene.Node):
    name = graphene.String(required=True)
    relation_id = graphene.Int()

    def resolve_relation_id(self, info, **kwargs):
        ret = None

        if sriutils.authorice_read_resource(info.context.user, self.handle_id):
            ret = getattr(self, 'relation_id', None)

        return ret

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

    @classmethod
    def get_connection_class(cls):
        class_name = '{}Connection'.format(cls)
        meta_class = type('Meta', (object,), dict(node=cls))
        the_class = type(class_name, (graphene.relay.Connection, ),
                            dict(Meta=meta_class))

        return the_class

    @classmethod
    def get_connection_resolver(cls):
        # do the import here to get it once it's loaded
        from .core import subclasses_interfaces

        def metatype_list_resolver(self, info, **args):
            ret = NodeHandle.objects.none()
            q_filters = []

            # get user's readable id list
            readable_ids = sriutils.get_ids_user_canread(info.context.user)
            # get filter
            filter = args.get('filter', {})

            # remove filter values of non existent nodetypes or
            # nodetypes that don't belong to this metatype
            subclasses = subclasses_interfaces[cls]
            subclasses_names = [str(x) for x in subclasses]

            filter_type_in = filter.get('type_in', [])
            filter_types = []

            for filter_nodetype in filter_type_in:
                if filter_nodetype in subclasses_names:
                    #filter_type_in.remove(filter_nodetype)
                    node_type = NodeType.get_from_camelcase(filter_nodetype)
                    filter_types.append(node_type)

            if filter_types:
                q_filters.append(Q(node_type__in=filter_types))
            else:
                q_filters.append(Q(node_type__in=[]))

            filter_name_contains = filter.get('name_contains', None)
            if filter_name_contains:
                q_filters.append(Q(node_name__icontains=filter_name_contains))

            # get filtered and ordered queryset
            if q_filters:
                full_filter = None
                for q_filter in q_filters:
                    if not full_filter:
                        full_filter = q_filter
                    else:
                        full_filter = full_filter & q_filter

                ret = NodeHandle.objects.filter(full_filter)
                ret = sriutils.trim_readable_queryset(ret, info.context.user)

            # get order values
            orderBy = args.get('orderBy', None)

            if orderBy:
                order = orderBy.split('_')[1]
                if order == 'ASC':
                    ret = ret.order_by('-node_name')
                elif order == 'DESC':
                    ret = ret.order_by('node_name')

            return ret

        return metatype_list_resolver


class PhysicalLogical(NINode):
    dependents = graphene.List(lambda:Logical)
    provider = graphene.Field(lambda:Relation)


class Logical(PhysicalLogical):
    part_of = graphene.Field(lambda:Physical)
    dependencies = graphene.List(lambda:PhysicalLogical)
    used_by = graphene.List(lambda:Relation)


class Relation(NINode):
    name = graphene.String(required= True)
    with_same_name = graphene.List(lambda:Relation)
    uses = graphene.List(lambda:Logical)
    provides = graphene.Field(NINode) # Physical or Logical
    owns = graphene.List(lambda:Physical)
    responsible_for = graphene.Field(lambda:Location)


class Physical(PhysicalLogical):
    location = graphene.Field(lambda:Location)
    has = graphene.List(lambda:Physical)
    part_of = graphene.Field(lambda:Logical)
    parent = graphene.List(lambda:PhysicalLogical)
    owner = graphene.Field(lambda:Relation)


class Location(NINode):
    parent = graphene.Field(lambda:Location)
    located_in = graphene.List(lambda:Physical)
    has = graphene.List(lambda:Location)
    responsible_for = graphene.Field(lambda:Relation)


class MetaType(graphene.Enum):
    Logical = 'Logical'
    Relation = 'Relation'
    Physical = 'Physical'
    Location = 'Location'


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
                relation_id = relation[relation_label][0]['relationship_id']

                if handle_id and \
                    NodeHandle.objects.filter(handle_id=handle_id) and \
                    sriutils.authorice_read_resource(\
                        info.context.user, handle_id):

                    ret = NodeHandle.objects.get(handle_id=handle_id)
                    ret.relation_id = relation_id

        return ret

    @staticmethod
    def multiple_relation_resolver(info, node, method_name, relation_label):
        ret = None

        if info.context and info.context.user.is_authenticated:
            relations = getattr(node, method_name)()
            nodes = relations.get(relation_label)

            id_list = []
            if nodes:
                for node in nodes:
                    relation_id = node['relationship_id']
                    node = node['node']
                    node_id = node.data.get('handle_id')
                    id_list.append((node_id, relation_id))

            id_list = sorted(id_list, key=lambda x: x[0])

            ret = []
            for handle_id, relation_id in id_list:
                nh = NodeHandle.objects.get(handle_id=handle_id)
                nh.relation_id = relation_id

                if sriutils.authorice_read_resource\
                    (info.context.user, nh.handle_id):

                    ret.append(nh)

        return ret


class PhysicalLogicalMixin:
    def resolve_dependents(self, info, **kwargs):
        return ResolverUtils.multiple_relation_resolver(
            info, self.get_node(), 'get_dependents', 'Depends_on')

    @classmethod
    def link_dependents(cls, user, physical_nh, logical_nh):
        logical_node = logical_nh.get_node()
        physical_handle_id = physical_nh.handle_id
        helpers.set_depends_on(user, logical_node, physical_handle_id)


    def resolve_provider(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), '_incoming', 'Provides')

    @classmethod
    def link_provider(cls, user, phylog_nh, relation_nh):
        helpers.set_provider(user, logical_node.get_node(),
                                relation_nh.handle_id)


class LogicalMixin(PhysicalLogicalMixin):
    def resolve_part_of(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_part_of', 'Part_of')

    def resolve_used_by(self, info, **kwargs):
        return ResolverUtils.multiple_relation_resolver(
            info, self.get_node(), '_incoming', 'Uses')

    def resolve_dependencies(self, info, **kwargs):
        return ResolverUtils.multiple_relation_resolver(
            info, self.get_node(), 'get_dependencies', 'Depends_on')

    @classmethod
    def link_part_of(cls, user, logical_nh, physical_nh):
        physical_node = physical_nh.get_node()
        logical_handle_id = logical_nh.handle_id
        helpers.set_part_of(user, physical_node, logical_handle_id)

    @classmethod
    def link_used_by(cls, user, logical_nh, relation_nh):
        helpers.set_user(user,
            logical_nh.get_node(), relation_nh.handle_id)

    @classmethod
    def link_dependencies(cls, user, logical1_nh, logical2_nh):
        logical1_node = logical1_nh.get_node()
        logical2_handle_id = logical2_nh.handle_id
        helpers.set_depends_on(user, logical1_node, logical2_handle_id)


class RelationMixin:
    def resolve_with_same_name(self, info, **kwargs):
        ret = None

        if info.context and info.context.user.is_authenticated:
            ids_samename = self.get_node().with_same_name().get('ids', None)
            if ids_samename and len(self.get_node().with_same_name()) > 0:
                ret = []
                for nh in NodeHandle.objects.filter(handle_id__in=ids_samename):
                    if sriutils.authorice_read_resource(\
                        info.context.user, nh.handle_id):
                        ret.append(nh)

        return ret

    def resolve_uses(self, info, **kwargs):
        return ResolverUtils.multiple_relation_resolver(
            info, self.get_node(), 'get_uses', 'Uses')

    def resolve_provides(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_provides', 'Provides')

    def resolve_owns(self, info, **kwargs):
        return ResolverUtils.multiple_relation_resolver(
            info, self.get_node(), 'get_owns', 'Owns')

    def resolve_responsible_for(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_responsible_for', 'Responsible_for')

    @classmethod
    def link_uses(cls, user, relation_nh, logical_nh):
        helpers.set_user(user,
            logical_nh.get_node(), relation_nh.handle_id)

    @classmethod
    def link_provides(cls, user, relation_nh, phylogical_nh):
        the_node = phylogical_nh.get_node()
        relation_handle_id = relation_nh.handle_id
        helpers.set_provider(user, the_node, relation_handle_id)

    @classmethod
    def link_owns(cls, user, relation_nh, physical_nh):
        physical_node = physical_nh.get_node()
        relation_handle_id = relation_nh.handle_id
        helpers.set_owner(user, physical_node, relation_handle_id)

    @classmethod
    def link_responsible_for(cls, user, relation_nh, location_nh):
        location_node = location_nh.get_node()
        relation_handle_id = relation_nh.handle_id
        helpers.set_responsible_for(user, location_node, relation_handle_id)


class PhysicalMixin(PhysicalLogicalMixin):
    def resolve_location(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_location', 'Located_in')

    def resolve_has(self, info, **kwargs):
        return ResolverUtils.multiple_relation_resolver(
            info, self.get_node(), 'get_has', 'Has')

    def resolve_part_of(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_part_of', 'Part_of')

    def resolve_parent(self, info, **kwargs):
        return ResolverUtils.multiple_relation_resolver(
            info, self.get_node(), 'get_parent', 'Has')

    def resolve_owner(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_relations', 'Owns')

    @classmethod
    def link_parent(cls, user, physical_nh, physical_parent_nh):
        # TODO: Make helper method
        handle_id = physical_nh.handle_id
        parent_handle_id = physical_parent_nh.handle_id

        q = """
            MATCH   (n:Node:Physical {handle_id: {handle_id}}),
                    (p:Node:Physical {handle_id: {parent_handle_id}})
            MERGE (n)<-[r:Has]-(p)
            RETURN n, r, p
            """

        result = nc.query_to_dict(nc.graphdb.manager, q,
                        handle_id=handle_id, parent_handle_id=parent_handle_id)

    @classmethod
    def link_has(cls, user, physical_nh, physical2_nh):
        physical_node = physical_nh.get_node()
        physical2_handle_id = physical2_nh.handle_id
        helpers.set_has(user, physical_node, physical2_handle_id)


class LocationMixin:
    def resolve_parent(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), 'get_parent', 'Has')

    def resolve_located_in(self, info, **kwargs):
        return ResolverUtils.multiple_relation_resolver(
            info, self.get_node(), 'get_located_in', 'Located_in')

    def resolve_has(self, info, **kwargs):
        return ResolverUtils.multiple_relation_resolver(
            info, self.get_node(), 'get_has', 'Has')

    def resolve_responsible_for(self, info, **kwargs):
        return ResolverUtils.single_relation_resolver(
            info, self.get_node(), '_incoming', 'Responsible_for')

    @classmethod
    def link_parent(cls, user, location_nh, parent_nh):
        parent_node = parent_nh.get_node()
        location_handle_id = location_nh.handle_id
        helpers.set_has(user, parent_node, location_handle_id)

    @classmethod
    def link_located_in(cls, user, location_nh, physical_nh):
        physical_node = physical_nh.get_node()
        location_handle_id = location_nh.handle_id
        helpers.set_location(user, physical_node, location_handle_id)

    @classmethod
    def link_has(cls, user, location_nh, has_nh):
        location_node = location_nh.get_node()
        has_id = has_nh.handle_id
        helpers.set_has(user, location_node, has_id)

    @classmethod
    def link_responsible_for(cls, user, location_nh, responsible_for_nh):
        location_node = location_nh.get_node()
        responsible_for_id = responsible_for_nh.handle_id
        helpers.set_responsible_for(user, location_node, responsible_for_id)
