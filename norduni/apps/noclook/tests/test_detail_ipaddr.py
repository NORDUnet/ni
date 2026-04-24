from .neo4j_base import NeoTestCase
from django.urls import reverse


class PeeringGroupDetailTest(NeoTestCase):

    def test_peering_group_detail(self):
        # Minimal
        unit = self.create_node('Unit1', 'unit', 'Logical')
        peering_group = self.create_node('TESTIX', 'peering-group', 'Logical')
        peering_partner = self.create_node('Awesome Co', 'peering-partner', 'Relation')

        group_node = peering_group.get_node()
        group_node.set_group_dependency(unit.handle_id, '172.16.0.0/12')
        group_node.set_group_dependency(unit.handle_id, 'fd00::/8')

        partner_node = peering_partner.get_node()
        partner_node.set_peering_group(peering_group.handle_id, '172.17.0.13')
        partner_node.set_peering_group(peering_group.handle_id, 'fd17:1234:abcd:1::1')

        resp = self.client.get(reverse('peering_group_detail', args=[peering_group.handle_id]))

        self.assertContains(resp, peering_group.node_name)
        self.assertContains(resp, peering_partner.node_name)
        self.assertContains(resp, unit.node_name)
        self.assertContains(resp, '172.16.0.0/12')
        self.assertContains(resp, '172.17.0.13')
        self.assertContains(resp, 'fd00::/8')
        self.assertContains(resp, 'fd17:1234:abcd:1::1')

    def test_peering_group_detail_dangling_network(self):
        unit = self.create_node('Unit1', 'unit', 'Logical')
        peering_group = self.create_node('TESTIX', 'peering-group', 'Logical')
        peering_partner = self.create_node('Awesome Co', 'peering-partner', 'Relation')

        # Add dependencies on unit with networks
        group_node = peering_group.get_node()
        group_node.set_group_dependency(unit.handle_id, '172.16.0.0/12')
        group_node.set_group_dependency(unit.handle_id, 'fd00::/8')

        # Set peering group for partner
        partner_node = peering_partner.get_node()
        partner_node.set_peering_group(peering_group.handle_id, '192.168.0.13')
        partner_node.set_peering_group(peering_group.handle_id, 'cd17:1234:abcd:1::1')

        resp = self.client.get(reverse('peering_group_detail', args=[peering_group.handle_id]))
        self.assertContains(resp, '172.16.0.0/12')
        self.assertContains(resp, 'fd00::/8')
        self.assertNotContains(resp, '192.168.0.13')
        self.assertNotContains(resp, 'cd17:1234:abcd:1::1')


class PeeringPartnerDetailTest(NeoTestCase):
    def test_peering_partner_detail(self):
        router = self.create_node('route1.test.dev', 'router')
        port = self.create_node('ae0', 'port')
        unit = self.create_node('Unit1', 'unit', 'Logical')
        peering_group = self.create_node('TESTIX', 'peering-group', 'Logical')
        peering_partner = self.create_node('Awesome Co', 'peering-partner', 'Relation')

        # Router-[:Has]->(port)<-[:Part_of]-(unit)
        router.get_node().set_has(port.handle_id)
        port.get_node().set_part_of(unit.handle_id)

        # Add dependencies on unit with networks
        group_node = peering_group.get_node()
        group_node.set_group_dependency(unit.handle_id, '172.16.0.0/12')
        group_node.set_group_dependency(unit.handle_id, 'fd00::/8')

        # Set peering group for partner
        partner_node = peering_partner.get_node()
        partner_node.set_peering_group(peering_group.handle_id, '172.17.0.13')
        partner_node.set_peering_group(peering_group.handle_id, 'fd17:1234:abcd:1::1')

        resp = self.client.get(reverse('peering_partner_detail', args=[peering_partner.handle_id]))

        self.assertContains(resp, peering_partner.node_name)
        self.assertContains(resp, peering_group.node_name)
        self.assertContains(resp, unit.node_name)
        self.assertContains(resp, port.node_name)
        self.assertContains(resp, router.node_name)
        self.assertContains(resp, unit.node_name)
        self.assertContains(resp, '172.16.0.0/12')
        self.assertContains(resp, '172.17.0.13')
        self.assertContains(resp, 'fd00::/8')
        self.assertContains(resp, 'fd17:1234:abcd:1::1')
