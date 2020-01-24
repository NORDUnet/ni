from .neo4j_base import NeoTestCase
from apps.noclook.views.edit import _handle_trunk_cable
from apps.noclook.forms.common import TrunkCableForm
from apps.noclook.models import UniqueIdGenerator, NordunetUniqueId
from apps.noclook import helpers


class TrunkCableTest(NeoTestCase):

    def test_standard_create(self):
        panel1, panel2 = self.two_nodes('switch', 10)

        form = TrunkCableForm({
            'trunk_base_name': 'NeatCable',
            'trunk_relationship_other': panel2.handle_id,
            'trunk_first_port': 1,
            'trunk_num_ports': 10,
        })

        result = _handle_trunk_cable(panel1.get_node(), form, self.user)
        # check that cables were actually added
        cables = self.get_cables(panel1.handle_id)
        for i in range(1, 11):
            self.assertIn('NeatCable_{}'.format(i), cables)
            NordunetUniqueId.objects.get(unique_id='NeatCable_{}'.format(i))
        self.assertEqual(len(cables), 10)
        self.assertTrue(result)
        # Cable should be of type Fixed
        self.assertEqual(cables['NeatCable_1'].get('cable_type'), 'Fixed')

    def test_standard_create_patch_panel(self):
        # Added due to patch panels not being a proper equipment type
        panel1, panel2 = self.two_nodes('patch-panel', 10)

        form = TrunkCableForm({
            'trunk_base_name': 'NeatCable',
            'trunk_relationship_other': panel2.handle_id,
            'trunk_first_port': 1,
            'trunk_num_ports': 10,
        })

        result = _handle_trunk_cable(panel1.get_node(), form, self.user)
        # check that cables were actually added
        cables = self.get_cables(panel1.handle_id)
        for i in range(1, 11):
            self.assertIn('NeatCable_{}'.format(i), cables)
        self.assertEqual(len(cables), 10)
        self.assertTrue(result)

    def test_bad_other(self):
        panel1, panel2 = self.two_nodes('patch-panel', 1)

        form = TrunkCableForm({
            'trunk_base_name': 'NeatCable',
            'trunk_relationship_other': 200,
            'trunk_first_port': 1,
            'trunk_num_ports': 1,
        })

        result = _handle_trunk_cable(panel1.get_node(), form, self.user)
        self.assertTrue(form.has_error('trunk_relationship_other'))
        self.assertFalse(result)

    def test_no_ports(self):
        panel1, panel2 = self.two_nodes('patch-panel', 0)

        form = TrunkCableForm({
            'trunk_base_name': 'NeatCable',
            'trunk_relationship_other': panel2.handle_id,
            'trunk_first_port': 1,
            'trunk_num_ports': 1,
        })

        _handle_trunk_cable(panel1.get_node(), form, self.user)

    def test_prefix_and_offset(self):
        panel1, panel2 = self.two_nodes('patch-panel', 0)

        form = TrunkCableForm({
            'trunk_base_name': 'NeatCable',
            'trunk_relationship_other': panel2.handle_id,
            'trunk_first_port': 8,
            'trunk_num_ports': 2,
            'trunk_prefix': 'p',
            'trunk_create_missing_ports': True,
        })

        result = _handle_trunk_cable(panel1.get_node(), form, self.user)
        # check that cables were actually added
        cables = self.get_cables(panel1.handle_id)
        for i in range(8, 10):
            self.assertIn('NeatCable_p{}'.format(i), cables)
        self.assertEqual(len(cables), 2)
        self.assertTrue(result)

    def test_zero_ports(self):
        panel1, panel2 = self.two_nodes('patch-panel', 2)

        form = TrunkCableForm({
            'trunk_base_name': 'NeatCable',
            'trunk_relationship_other': panel2.handle_id,
            'trunk_first_port': 1,
            'trunk_num_ports': 0,
        })

        _handle_trunk_cable(panel1.get_node(), form, self.user)
        # check that cables were actually added
        cables = self.get_cables(panel1.handle_id)
        self.assertEqual(len(cables), 0)

    def test_not_enough_ports(self):
        panel1, panel2 = self.two_nodes('patch-panel', 2)
        form = TrunkCableForm({
            'trunk_base_name': 'NeatCable',
            'trunk_relationship_other': panel2.handle_id,
            'trunk_first_port': 1,
            'trunk_num_ports': 3,
        })

        _handle_trunk_cable(panel1.get_node(), form, self.user)
        self.assertTrue(form.has_error('trunk_create_missing_ports'))

        # check that no cables were created
        cables = self.get_cables(panel1.handle_id)
        self.assertEqual(len(cables), 0)

    def test_force_create_ports(self):
        panel1, panel2 = self.two_nodes('patch-panel', 2)
        form = TrunkCableForm({
            'trunk_base_name': 'NeatCable',
            'trunk_relationship_other': panel2.handle_id,
            'trunk_first_port': 1,
            'trunk_num_ports': 3,
            'trunk_create_missing_ports': True,
        })

        _handle_trunk_cable(panel1.get_node(), form, self.user)
        self.assertEqual(form.errors, {})

        # check that no cables were created
        cables = self.get_cables(panel1.handle_id)
        self.assertEqual(len(cables), 3)

    def test_cable_already_exist(self):
        panel1, panel2 = self.two_nodes('patch-panel', 2)
        self.create_node('NeatCable_2', 'cable')
        form = TrunkCableForm({
            'trunk_base_name': 'NeatCable',
            'trunk_relationship_other': panel2.handle_id,
            'trunk_first_port': 1,
            'trunk_num_ports': 2,
            'trunk_create_missing_ports': True,
        })

        _handle_trunk_cable(panel1.get_node(), form, self.user)
        self.assertTrue(form.has_error('trunk_base_name'))

        # check that no cables were created
        cables = self.get_cables(panel1.handle_id)
        self.assertEqual(len(cables), 0)

    def test_no_unique_id_gen(self):
        panel1, panel2 = self.two_nodes('patch-panel', 2)
        form = TrunkCableForm({
            'trunk_relationship_other': panel2.handle_id,
            'trunk_first_port': 1,
            'trunk_num_ports': 2,
        })

        _handle_trunk_cable(panel1.get_node(), form, self.user)

        self.assertTrue(form.has_error('trunk_base_name'))
        # check that no cables were created
        cables = self.get_cables(panel1.handle_id)
        self.assertEqual(len(cables), 0)

    def test_with_unique_id(self):
        id_generator, created = UniqueIdGenerator.objects.get_or_create(
            name='test_cable_id',
            base_id_length=6,
            zfill=True,
            prefix='TEST-',
            creator=self.user
        )
        panel1, panel2 = self.two_nodes('patch-panel', 2)
        form = TrunkCableForm({
            'trunk_relationship_other': panel2.handle_id,
            'trunk_first_port': 1,
            'trunk_num_ports': 2,
        })

        _handle_trunk_cable(panel1.get_node(), form, self.user)

        self.assertEqual(form.errors, {})
        cables = self.get_cables(panel1.handle_id)
        self.assertNotIn('_1', cables)
        self.assertEqual(len(cables), 2)
        self.assertIn('TEST-000001_1', cables)

    # Helpers
    def two_nodes(self, slug, num_ports, start_port=1):
        panel1 = self.create_node('node1', slug)
        panel_node1 = panel1.get_node()

        panel2 = self.create_node('node2', slug)
        panel_node2 = panel2.get_node()

        for i in range(start_port, start_port + num_ports):
            helpers.create_port(panel_node1, str(i), self.user)
            helpers.create_port(panel_node2, str(i), self.user)

        return panel1, panel2

    def get_cables(self, handle_id):
        q = """
            MATCH (n:Node {handle_id: $handle_id})-[:Has]->(p:Port)<-[:Connected_to]-(c:Cable)
            RETURN c as cable
            """
        return {c.get('cable').get('name'): c.get('cable') for c in self.query_to_list(q, handle_id=handle_id)}
