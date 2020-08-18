# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import norduniclient as nc

from apps.noclook.models import NodeHandle, NodeType, Dropdown, Choice
from apps.noclook.management.commands.datafaker import Command as DFCommand
from django.core.management import call_command
from django.test.utils import override_settings
from norduniclient.exceptions import UniqueNodeError, NodeNotFound
import norduniclient.models as ncmodels

from ..neo4j_base import NeoTestCase


class DataFakerTest(NeoTestCase):
    cmd_name = DFCommand.cmd_name
    test_node_num = 5

    @override_settings(DEBUG=True)
    def test_create_organizations(self):
        # check that there's not any node of the generated types
        all_node_types = NodeType.objects.filter(type__in=DFCommand.generated_types)
        self.assertFalse(
            NodeHandle.objects.filter(node_type__in=all_node_types).exists()
        )

        # call organization generator
        call_command(self.cmd_name,
            **{
                DFCommand.option_organizations: self.test_node_num,
                'verbosity': 0,
            }
        )

        # call equipment and cables generator
        call_command(self.cmd_name,
            **{
                DFCommand.option_equipment: self.test_node_num,
                'verbosity': 0,
            }
        )

        # call peering generator
        call_command(self.cmd_name,
            **{
                DFCommand.option_peering: self.test_node_num,
                'verbosity': 0,
            }
        )

        # call optical generator
        call_command(self.cmd_name,
            **{
                DFCommand.option_optical: self.test_node_num,
                'verbosity': 0,
            }
        )

        # check that there's nodes from the generated types
        self.assertTrue(
            NodeHandle.objects.filter(node_type__in=all_node_types).exists()
        )

        # delete all
        call_command(self.cmd_name,
            **{
                DFCommand.option_deleteall: 1,
                'verbosity': 0,
            }
        )

        # check there's nothing left
        self.assertFalse(
            NodeHandle.objects.filter(node_type__in=all_node_types).exists()
        )
