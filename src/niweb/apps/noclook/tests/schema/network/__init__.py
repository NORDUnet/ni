# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from django.core.management import call_command

from apps.noclook.management.commands.datafaker import Command as DFCommand
from apps.noclook.tests.schema.base import Neo4jGraphQLGenericTest

class TestContext():
    def __init__(self, user, *ignore):
        self.user = user

class Neo4jGraphQLNetworkTest(Neo4jGraphQLGenericTest):
    def create_organization_nodes(self, entity_num):
        call_command(DFCommand.cmd_name,
            **{
                DFCommand.option_organizations: entity_num,
                'verbosity': 0,
            }
        )

    def create_equicables_nodes(self, entity_num):
        call_command(DFCommand.cmd_name,
            **{
                DFCommand.option_equipment: entity_num,
                'verbosity': 0,
            }
        )

    def create_peering_nodes(self, entity_num):
        call_command(DFCommand.cmd_name,
            **{
                DFCommand.option_peering: entity_num,
                'verbosity': 0,
            }
        )

    def create_optical_nodes(self, entity_num):
        call_command(DFCommand.cmd_name,
            **{
                DFCommand.option_optical: entity_num,
                'verbosity': 0,
            }
        )

    def create_logical_nodes(self, entity_num):
        call_command(DFCommand.cmd_name,
            **{
                DFCommand.option_location: entity_num,
                'verbosity': 0,
            }
        )
