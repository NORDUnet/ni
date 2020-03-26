# -*- coding: utf-8 -*-

from django.core.management import call_command

import norduniclient as nc
from norduniclient.exceptions import UniqueNodeError, NodeNotFound
import norduniclient.models as ncmodels

from apps.noclook.models import NodeHandle, NodeType, Dropdown, Choice

from ..neo4j_base import NeoTestCase
from .fileutils import write_string_to_disk
from .test_csvimport import CsvImportTest

__author__ = 'ffuentes'

class DataFixerImportTest(NeoTestCase):
    cmd_name = 'datafixer'
    import_name = 'csvimport'

    def setUp(self):
        super(DataFixerImportTest, self).setUp()
        self.organizations_file = write_string_to_disk(CsvImportTest.organizations_str)

    def tearDown(self):
        super(DataFixerImportTest, self).tearDown()

    def count_different_orgids(self):
        q = """
            MATCH (o:Organization)
            RETURN COUNT(DISTINCT o.organization_id) AS orgs
            """
        res = nc.query_to_dict(nc.graphdb.manager, q)

        return res['orgs']

    def has_raw_values(self, all_organizations):
        has_raw_values = False

        org_types_drop = Dropdown.objects.get(name='organization_types')
        org_types = Choice.objects.filter(dropdown=org_types_drop)

        for organization in all_organizations:
            orgnode = organization.get_node()
            org_type = orgnode.data.get('type', None)

            if org_type and not org_types.filter(value=org_type).exists():
                has_raw_values = True
                break

        return has_raw_values

    def test_organizations_import(self):
        # call csvimport command (verbose 0)
        call_command(
            self.import_name,
            organizations=self.organizations_file,
            verbosity=0,
        )

        # count organizations
        organization_type = NodeType.objects.get_or_create(
                                type='Organization', slug='organization')[0]
        all_organizations = NodeHandle.objects.filter(node_type=organization_type)
        orgs_num = all_organizations.count()

        # count unique org_ids
        orgids = self.count_different_orgids()
        self.assertTrue( orgids < orgs_num)

        # check it has raw values
        has_raw_values = self.has_raw_values(all_organizations)
        self.assertTrue(has_raw_values)

        # call fixer command
        call_command(
            self.cmd_name,
            fixtestdata=True,
            verbosity=0,
        )

        # count unique org_ids
        orgids = self.count_different_orgids()

        self.assertTrue( orgids == orgs_num)

        # check it hasn't raw values
        has_raw_values = self.has_raw_values(all_organizations)
        self.assertFalse(has_raw_values)
