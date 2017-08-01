from .neo4j_base import NeoTestCase
from apps.noclook import helpers


class ExportSiteTest(NeoTestCase):
    def setUp(self):
        super(ExportSiteTest, self).setUp()

    def test_export_empty_site(self):
        site = helpers.get_unique_node_handle(self.user, "Test site", "site", "Location")
        resp = self.client.get(self.get_full_url(site) + "export")
        self.assertEquals('attachment; filename="Site.Test site_export.json"', resp['Content-Disposition'])
        self.assertEquals('application/json', resp['Content-Type'])
        self.assertEquals([], resp.json())

    def test_populated_site(self):
        # Setup test data
        site = helpers.get_unique_node_handle(self.user, "Test site", "site", "Location")
        site_node = site.get_node()
        rack = helpers.get_generic_node_handle(self.user, "A.01", "rack", "Location")
        helpers.set_has(self.user, site_node, rack.handle_id)
        odf = helpers.get_unique_node_handle(self.user, "NI-TEST-ODF-01", "odf", "Physical")
        odf_node = odf.get_node()
        helpers.dict_update_node(self.user, odf.handle_id, {"max_ports": 24})
        helpers.set_location(self.user, odf_node, rack.handle_id)

        helpers.create_port(odf_node, "1", self.user)
        helpers.create_port(odf_node, "2", self.user)
        helpers.create_port(odf_node, "3", self.user)

        router = helpers.get_unique_node_handle(self.user, "ni-test.routers.nordu.net", "router", "Physical")
        router_node = router.get_node()
        helpers.dict_update_node(self.user, router.handle_id, {"operational_state": "Testing", "rack_units": 2})
        helpers.set_location(self.user, router_node, rack.handle_id)
        odf2 = helpers.get_generic_node_handle(self.user, "NI-TEST-ODF-02", "odf", "Physical")
        odf2_node = odf2.get_node()
        helpers.set_location(self.user, odf2_node, site.handle_id)
        # Done setting up testdata

        resp = self.client.get(self.get_full_url(site) + "export")
        self.assertEquals('application/json', resp['Content-Type'])
        result = resp.json()

        # verify data
        self.assertEquals(2, len(result))
        self.assertDictContainsSubset({'name': 'A.01', 'node_type': 'Rack'}, result[0])
        self.assertDictContainsSubset({'node_type': 'ODF', 'name': 'NI-TEST-ODF-02'}, result[1])
        # Check racked equipment
        rack_equp = result[0]['children']
        self.assertEquals(2, len(rack_equp))
        odf1_result = rack_equp[0]
        self.assertDictContainsSubset({'node_type': 'ODF', 'name': 'NI-TEST-ODF-01', 'max_ports': 24}, odf1_result)
        # Check ODF ports
        odf1_ports = odf1_result['children']
        self.assertEquals(3, len(odf1_ports))
        self.assertDictContainsSubset({'node_type': 'Port', 'name': '1', 'port_type': ''}, odf1_ports[0])
        self.assertDictContainsSubset({'node_type': 'Port', 'name': '2', 'description': ''}, odf1_ports[1])
        self.assertDictContainsSubset({'node_type': 'Port', 'name': '3'}, odf1_ports[2])

        # Check router
        router = rack_equp[1]
        self.assertDictContainsSubset({'node_type': 'Router', 'name': 'ni-test.routers.nordu.net'}, router)

    def test_decommissioned_equipment(self):
        self.skipTest('Not working as expected yet.')
        # Setup test data
        site = helpers.get_unique_node_handle(self.user, "Test site", "site", "Location")
        site_node = site.get_node()
        rack = helpers.get_generic_node_handle(self.user, "A.01", "rack", "Location")
        helpers.set_has(self.user, site_node, rack.handle_id)
        odf = helpers.get_unique_node_handle(self.user, "NI-TEST-ODF-01", "odf", "Physical")
        odf_node = odf.get_node()
        helpers.dict_update_node(self.user, odf.handle_id, {"max_ports": 24})
        helpers.set_location(self.user, odf_node, rack.handle_id)

        decom_on = helpers.get_unique_node_handle(self.user, "NI-TEST-ON-01", "optical-node", "Physical")
        decom_on_node = decom_on.get_node()
        helpers.dict_update_node(self.user, decom_on.handle_id, {"operational_state": "Decommissioned"})
        helpers.set_location(self.user, decom_on_node, rack.handle_id)

        helpers.create_port(decom_on_node, "1", self.user)
        helpers.create_port(decom_on_node, "2", self.user)
        # End test data

        resp = self.client.get(self.get_full_url(site) + "export")
        self.assertEquals('application/json', resp['Content-Type'])
        result = resp.json()

        # verify data
        self.assertEquals(1, len(result))
        rack_result = result[0]
        self.assertDictContainsSubset({'name': 'A.01', 'node_type': 'Rack'}, rack_result)
        rack_equip = rack_result['children']
        # Decommissioned equipment should be gone
        self.assertEquals(1, len(rack_equip))
        self.assertDictContainsSubset({'node_type': 'ODF', 'name': 'NI-TEST-ODF-01'}, rack_equip[0])
        self.assertEquals(2, len(rack_equip[0]['children']))

    def test_export_optical_node(self):
        # Setup test data
        site = helpers.get_unique_node_handle(self.user, "Test site", "site", "Location")

        optical_node = helpers.get_unique_node_handle(self.user, "NI-TEST-ROADM", "optical-node", "Physical")
        on_node = optical_node.get_node()
        helpers.set_location(self.user, on_node, site.handle_id)
        helpers.dict_update_node(self.user, optical_node.handle_id, {"operational_state": "In service", "rack_units": "2", "type": "ciena6500"})
        # start testing
        resp = self.client.get(self.get_full_url(site) + "export")
        self.assertEquals('application/json', resp['Content-Type'])
        result = resp.json()

        # verify data
        self.assertEquals(1, len(result))
        on_result = result[0]
        self.assertEqual({u'name': u'NI-TEST-ROADM', u'node_type': u'Optical Node', u'type': u'ciena6500', u'rack_units': u'2', u'children': [], u'operational_state': u'In service'}, on_result)
