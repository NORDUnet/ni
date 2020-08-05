

from .neo4j_base import NeoTestCase
from apps.noclook import helpers


class FormadataApiTest(NeoTestCase):
    def setUp(self):
        super(FormadataApiTest, self).setUp()
        self.base_url = '/api/formdata/{slug}/'
        site1 = self.create_site('UK-HEX')
        site2 = self.create_site('DK-ORE')
        rack1 = self.create_rack('A.01')
        rack2 = self.create_rack('B.02')

        self.sites = [
            [site1.handle_id, site1.node_name],
            [site2.handle_id, site2.node_name],
        ]

        self.racks = [
            [rack1.handle_id, rack1.node_name],
            [rack2.handle_id, rack2.node_name],
        ]

    def test_formdata_slug_sites(self):
        resp = self.client.get(self.base_url.format(slug='site'))
        sites = resp.json()

        self.assertIn(self.sites[0], sites)
        self.assertIn(self.sites[1], sites)

    def test_formdata_sort_order(self):
        resp = self.client.get(self.base_url.format(slug='site'))
        site_names = [name for _id, name in resp.json()]

        real_site_names = sorted([name for _id, name in self.sites])
        self.assertEqual(real_site_names[0], site_names[0])

    def test_formdata_slug_racks(self):
        resp = self.client.get(self.base_url.format(slug='rack'))
        racks = resp.json()

        self.assertEqual(self.racks, racks)

    def create_site(self, name):
        return helpers.create_unique_node_handle(self.user, name, "site", "Location")

    def create_rack(self, name):
        return helpers.create_unique_node_handle(self.user, name, "rack", "Location")
