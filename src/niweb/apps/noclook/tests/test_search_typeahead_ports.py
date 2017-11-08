from .neo4j_base import NeoTestCase
from apps.noclook import helpers


class SearchTypeaheadPortsCase(NeoTestCase):
    def setUp(self):
        super(SearchTypeaheadPortsCase, self).setUp()
        self.typeahead_url = "/search/typeahead/ports"
        site = helpers.create_unique_node_handle(self.user, "UK-HEX", "site", "Location")
        rack = helpers.get_generic_node_handle(self.user, "A.01", "rack", "Location")
        helpers.set_has(self.user, site.get_node(), rack.handle_id)

        odf1 = helpers.create_unique_node_handle(self.user, "test-odf1", "odf", "Physical")
        odf1_node = odf1.get_node()
        helpers.set_location(self.user, odf1_node, rack.handle_id)
        helpers.create_port(odf1_node, "1+2", self.user)
        helpers.create_port(odf1_node, "3+4", self.user)

        odf2 = helpers.create_unique_node_handle(self.user, "other-odf2", "odf", "Physical")
        odf2_node = odf2.get_node()
        helpers.set_location(self.user, odf2_node, site.handle_id)
        helpers.create_port(odf2_node, "11+12", self.user)
        helpers.create_port(odf2_node, "13+14", self.user)

        router = helpers.create_unique_node_handle(self.user, "uk-hex.nordu.net", "router", "Physical")
        router_node = router.get_node()
        helpers.set_location(self.user, router_node, site.handle_id)
        helpers.create_port(router_node, "ge-0/0/1", self.user)
        helpers.create_port(router_node, "ge-0/0/2", self.user)
        helpers.create_port(router_node, "ge-0/1/1", self.user)

    def test_one_result(self):
        resp = self.client.get(self.typeahead_url, {"query": "hex odf 3+4"})
        result = resp.json()
        self.assertEquals(1, len(result))
        odf = result[0]
        self.assertEquals("UK-HEX A.01 test-odf1 3+4", odf.get("name"))

    def test_no_result(self):
        resp = self.client.get(self.typeahead_url, {"query": "ore2 odf"})
        result = resp.json()
        self.assertEquals(0, len(result))

    def test_multiple_results(self):
        resp = self.client.get(self.typeahead_url, {"query": "ge-"})
        result = resp.json()
        self.assertEquals(3, len(result))

    def test_empty_query(self):
        resp = self.client.get(self.typeahead_url, {"query": ""})
        result = resp.json()
        self.assertEquals(0, len(result))

    def test_no_query(self):
        resp = self.client.get(self.typeahead_url, {})
        result = resp.json()
        self.assertEquals(0, len(result))

    def test_escapes_regex(self):
        resp = self.client.get(self.typeahead_url, {"query": ".*"})
        result = resp.json()
        self.assertEquals(0, len(result))

