# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.management.commands.datafaker import Command as DFCommand
from apps.noclook.models import NodeHandle, NodeType
from collections import OrderedDict
from django.utils.dateparse import parse_datetime
from graphene import relay
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLNetworkTest

class SimpleListTest(Neo4jGraphQLNetworkTest):
    #test_types = DFCommand.generated_types
    test_types = [
        'Customer', 'End User', 'Site Owner', 'Provider', 'Peering Group', 'Peering Partner',
        'Cable', 'Port', 'Host']

    def test_simple_list(self):
        # query all available types
        for type_name in self.test_types:
            if NodeType.objects.filter(type=type_name).exists():
                nodetype = NodeType.objects.get(type=type_name)
                components = type_name.split(' ')
                # type name camelcased
                type_name_cc = components[0].lower() + ''.join(x.title() for x in components[1:])
                graph_type_name = type_name.replace(' ', '')
                fmt_type_name = graph_type_name.lower()

                query = '''
                {{
                  all_{}s {{
                    id
                    handle_id
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
                        ('handle_id', str(node.handle_id)),
                        ('node_name', node.node_name)
                    ])
                    node_dict = dict(node_dict)
                    node_list.append(node_dict)

                expected = {
                    'all_{}s'.format(fmt_type_name): node_list,
                }

                result = schema.execute(query, context=self.context)
                assert not result.errors, pformat(result.errors, indent=1)

                assert result.data == expected, '\n{} \n != {}'.format(
                                                    pformat(result.data, indent=1),
                                                    pformat(expected, indent=1)
                                                )
