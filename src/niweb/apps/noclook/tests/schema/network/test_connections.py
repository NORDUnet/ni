# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import logging

from apps.noclook.management.commands.datafaker import Command as DFCommand
from apps.noclook.models import NodeHandle, NodeType
from collections import OrderedDict
from django.utils.dateparse import parse_datetime
from graphene import relay
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLNetworkTest

test_types = [
    ## organizations
    'Customer', 'End User', 'Site Owner', 'Provider',
    ## peering
    'Peering Group', 'Peering Partner',
    ## equipment and cables
    'Cable', 'Port', 'Host', 'Router', 'Optical Node', 'ODF',
    ## optical layers
    'Optical Filter', 'Optical Link', 'Optical Multiplex Section', 'Optical Path',
    ## locations
    'Site',
]

logger = logging.getLogger(__name__)


def simple_type_check(self, test_f, type_name):
    if NodeType.objects.filter(type=type_name).exists():
        nodetype = NodeType.objects.get(type=type_name)
        components = type_name.split(' ')

        # type name camelcased
        type_name_cc = components[0].lower() + ''.join(x.title() for x in components[1:])
        graph_type_name = type_name.replace(' ', '')
        fmt_type_name = graph_type_name.lower()

        query, expected = test_f(self, nodetype, type_name_cc, graph_type_name, fmt_type_name)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        assert result.data == expected, '\n{} \n != {}'.format(
                                            pformat(result.data, indent=1),
                                            pformat(expected, indent=1)
                                        )

def simple_type_loop(self, test_f):
    # query all available types
    for type_name in test_types:
        simple_type_check(self, test_f, type_name)


class NetworkListTest(Neo4jGraphQLNetworkTest):
    def setUp(self):
        super(NetworkListTest, self).setUp()
        # create nodes
        entity_num = 3

        self.create_organization_nodes(entity_num)
        self.create_equicables_nodes(entity_num)
        self.create_peering_nodes(entity_num)
        self.create_optical_nodes(entity_num)
        self.create_logical_nodes(entity_num)


class SimpleListTest(NetworkListTest):
    def test_simple_list(self):
        def test_f(self, nodetype, type_name_cc, graph_type_name, fmt_type_name):
            query = '''
            {{
              all_{}s {{
                id
                node_name
              }}
            }}
            '''.format(fmt_type_name)

            nodes = NodeHandle.objects.filter(node_type=nodetype).order_by('node_name')
            node_list = []

            for node in nodes:
                relay_id = relay.Node.to_global_id(
                                graph_type_name, str(node.handle_id))
                node_dict = OrderedDict([
                    ('id', str(relay_id)),
                    ('node_name', node.node_name)
                ])
                node_dict = dict(node_dict)
                node_list.append(node_dict)

            expected = {
                'all_{}s'.format(fmt_type_name): node_list,
            }

            return (query, expected)

        simple_type_loop(self, test_f)


class SimpleConnectionTest(NetworkListTest):
    def test_simple_connection_list(self):
        def test_f(self, nodetype, type_name_cc, graph_type_name, fmt_type_name):
            query = '''
            {{
              {}s(orderBy: handle_id_DESC){{
                edges{{
                  node{{
                    id
                    name
                  }}
                }}
              }}
            }}
            '''.format(type_name_cc)

            nodes = NodeHandle.objects.filter(node_type=nodetype).order_by('-handle_id')
            node_list = []

            for node in nodes:
                relay_id = relay.Node.to_global_id(
                                graph_type_name, str(node.handle_id))
                node_dict = OrderedDict([
                    ('id', str(relay_id)),
                    ('name', node.node_name)
                ])
                node_dict = dict(node_dict)
                node_list.append({'node': node_dict})

            expected = {
                '{}s'.format(type_name_cc): {
                    'edges': node_list
                },
            }

            return (query, expected)

        simple_type_loop(self, test_f)


class FilteredConnectionTest(NetworkListTest):
    def test_filtered_connection_list(self):
        def get_test_f(self, filter_field, filterd_qs, field_value):
            filter_str_base = ", filter:{{ AND:[{{ {filter_field}: \"{field_value}\" }}] }}"
            filter_str = filter_str_base.format(
                filter_field=filter_field, field_value=field_value
            )

            def test_f(self, nodetype, type_name_cc, graph_type_name, fmt_type_name):
                query = '''
                {{
                  {typename}s(orderBy: handle_id_DESC {filter_str}){{
                    edges{{
                      node{{
                        id
                        name
                      }}
                    }}
                  }}
                }}
                '''.format(typename=type_name_cc, filter_str=filter_str)

                node_list = []

                for node in filterd_qs:
                    relay_id = relay.Node.to_global_id(
                                    graph_type_name, str(node.handle_id))
                    node_dict = OrderedDict([
                        ('id', str(relay_id)),
                        ('name', node.node_name)
                    ])
                    node_dict = dict(node_dict)
                    node_list.append({'node': node_dict})

                expected = {
                    '{}s'.format(type_name_cc): {
                        'edges': node_list
                    },
                }

                return (query, expected)

            return test_f

        type_filters = OrderedDict()


        # loop over the tested types
        for node_type in test_types:
            if NodeType.objects.filter(type=node_type).exists():
                name_filter_variations = OrderedDict()

                nodetype = NodeType.objects.get(type=node_type)
                nodes = NodeHandle.objects.filter(node_type=nodetype).order_by('-handle_id')

                # get one of the entities
                the_node = nodes.first()

                # build the filters and the expected querysets

                # name
                filterd_qs = nodes.filter(node_name=the_node.node_name)
                name_filter_variations['name'] = {
                    'queryset': filterd_qs,
                    'field_value': the_node.node_name
                }

                # name_not
                filterd_qs = nodes.exclude(node_name=the_node.node_name)
                name_filter_variations['name_not'] = {
                    'queryset': filterd_qs,
                    'field_value': the_node.node_name
                }

                # name_contains
                filterd_qs = nodes.filter(node_name__icontains=the_node.node_name)
                name_filter_variations['name_contains'] = {
                    'queryset': filterd_qs,
                    'field_value': the_node.node_name
                }

                # name_not_contains
                filterd_qs = nodes.exclude(node_name__icontains=the_node.node_name)
                name_filter_variations['name_not_contains'] = {
                    'queryset': filterd_qs,
                    'field_value': the_node.node_name
                }

                # name_starts_with
                filterd_qs = nodes.filter(node_name__istartswith=the_node.node_name)
                name_filter_variations['name_starts_with'] = {
                    'queryset': filterd_qs,
                    'field_value': the_node.node_name
                }

                # name_not_starts_with
                filterd_qs = nodes.exclude(node_name__istartswith=the_node.node_name)
                name_filter_variations['name_not_starts_with'] = {
                    'queryset': filterd_qs,
                    'field_value': the_node.node_name
                }

                # name_ends_with
                filterd_qs = nodes.filter(node_name__iendswith=the_node.node_name)
                name_filter_variations['name_ends_with'] = {
                    'queryset': filterd_qs,
                    'field_value': the_node.node_name
                }

                # name_not_ends_with
                filterd_qs = nodes.exclude(node_name__iendswith=the_node.node_name)
                name_filter_variations['name_not_ends_with'] = {
                    'queryset': filterd_qs,
                    'field_value': the_node.node_name
                }

                type_filters[node_type] = name_filter_variations

        # loop over the built filter and the expected queryset
        for node_type in test_types:
            if node_type in type_filters.keys():
                name_filter_variations = type_filters[node_type]

                for filter_field, dict_value in name_filter_variations.items():
                    filterd_qs = dict_value['queryset']
                    field_value = dict_value['field_value']
                    test_f = get_test_f(self, filter_field, filterd_qs, field_value)
                    simple_type_check(self, node_type, test_f)
