from .neo4j_base import NeoTestCase
from apps.noclook import helpers
import io


class ImportSiteTest(NeoTestCase):
    def setUp(self):
        super(ImportSiteTest, self).setUp()

    def test_import_empty(self):
        resp, site = self.import_to_site({
          "import": True,
        })
        self.assertRedirects(resp, self.get_full_url(site))

    def test_import_form(self):
        resp,site = self.import_to_site({
          "import": True,
          "Rack1.node_type": "Rack",
          "Rack1.name": "Sweet rack1",
          "Rack1.height": "",
          "Rack1.width": "",
          "Rack1.depth": "",
          "Rack1.rack_units": "48",
          "Rack1.ODF1.node_type": "ODF",
          "Rack1.ODF1.name": "TEST-ODF-01",
          "Rack1.ODF1.rack_units": "2",
          "Rack1.ODF1.Port1.node_type": "Port",
          "Rack1.ODF1.Port1.name": "1+2",
          "Rack1.ODF1.Port1.port_type": "E2000",
        })

        self.assertRedirects(resp, self.get_full_url(site))
        
        node = site.get_node()
        racks = node.get_has()
        self.assertEquals(1, len(racks))
        
        rack = racks["Has"][0]["node"]
        self.assertEquals("Sweet rack1", rack.data["name"])
        self.assertEquals("48", rack.data["rack_units"])
        
        equipment = rack.get_located_in()
        self.assertEqual(1, len(equipment))

        odf = equipment["Located_in"][0]["node"]
        self.assertEquals("TEST-ODF-01", odf.data["name"])
        self.assertEquals("2", odf.data["rack_units"])
        
        ports = odf.get_ports()
        self.assertEqual(1, len(ports))
        port = ports["Has"][0]["node"]
        self.assertEquals("1+2", port.data["name"])
        self.assertEquals("E2000", port.data["port_type"])

    def test_import_form_with_one_error(self):
        resp,site = self.import_to_site({
            "import": True,
            "Rack1.name": "",
            "Rack1.node_type": "Rack",
        })

        #Make sure we got an error page
        self.assertEquals(200, resp.status_code)
        self.assertContains(resp, "There is one error please fix it.")

    def test_import_form_with_two_errors(self):
        resp,site = self.import_to_site({
            "import": True,
            "Rack1.name": "",
            "Rack1.node_type": "Rack",
            "Rack2.name": "",
            "Rack2.node_type": "Rack",
        })

        #Make sure we got an error page
        self.assertEquals(200, resp.status_code)
        self.assertContains(resp, "There are 2 errors please fix them.")

    def test_import_direct_empty_file(self):
        resp, site = self.import_to_site({
            "import": True,
            "file": io.StringIO(u"[]"),
        })
        self.assertRedirects(resp, self.get_full_url(site))

    def test_import_file(self):
        fake_file = u'''[{
                "name": "RC/P01",
                "height": "",
                "width": "",
                "depth": "",
                "rack_units": "",
                "node_type": "Rack",
                "children": [
                    {
                      "name": "TEST-ODF-01",
                      "max_number_of_ports": "",
                      "rack_units": "",
                      "node_type": "ODF"
                    }]
              }]'''
        resp, site = self.import_to_site({
            "file": io.StringIO(fake_file),
        })
        self.assertEquals(200, resp.status_code)
        site_data = site.get_node().data
        self.assertContains(resp, 'Import into Site: '+site_data['name'])
        self.assertContains(resp, 'name="Rack1.node_type" value="Rack"')
        self.assertContains(resp, 'name="Rack1.name" value="RC/P01"')
        self.assertContains(resp, 'name="Rack1.width" value=""')
        self.assertContains(resp, 'name="Rack1.depth" value=""')
        self.assertContains(resp, 'name="Rack1.height" value=""')
        self.assertContains(resp, 'name="Rack1.rack_units" value=""')
        self.assertContains(resp, 'name="Rack1.ODF1.node_type" value="ODF"')
        self.assertContains(resp, 'name="Rack1.ODF1.name" value="TEST-ODF-01"')
        self.assertContains(resp, 'name="Rack1.ODF1.rack_units" value=""')
        self.assertContains(resp, 'name="Rack1.ODF1.max_number_of_ports" value=""')
        

    def test_import_optical_node_new_type(self):
        resp, site = self.import_to_site({
            "import": True,
            "Optical Node1.node_type": "Optical Node",
            "Optical Node1.name": "TestROADAM",
            "Optical Node1.type": "SpecialROADM",
            "Optical Node1.operational_state": "In service",
            "Optical Node1.rack_units": "2",
        })
        # Maybe we should have an error page instad?
        self.assertRedirects(resp, self.get_full_url(site))

    def import_to_site(self,data):
        site = self.create_site()
        resp = self.client.post(self.get_full_url(site)+"import", data)
        return resp, site

    def create_site(self, name="Test site"):
        return helpers.get_unique_node_handle(self.user, name, "site", "Location")
