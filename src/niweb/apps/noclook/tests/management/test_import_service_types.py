# -*- coding: utf-8 -*-

from apps.noclook.models import ServiceType, ServiceClass
from django.core.management import call_command

from ..neo4j_base import NeoTestCase
import os

__author__ = 'ffuentes'

class ImportServiceTypesTest(NeoTestCase):
    cmd_name = 'import_service_types'

    def test_import_service_types(self):
        # call import_service_types command
        
        dirpath = os.path.dirname(os.path.realpath(__file__))
        csv_file = \
            '{}/../../../../../scripts/service_types/ndn_service_types.csv'\
                .format(dirpath)

        call_command(
            self.cmd_name,
            csv_file=csv_file
        )

        self.assertTrue(ServiceType.objects.all().exists())
        self.assertTrue(ServiceClass.objects.all().exists())
