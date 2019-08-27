# -*- coding: utf-8 -*-
from ..neo4j_base import NeoTestCase
from apps.noclook.forms import nordunet as forms
from apps.noclook.models import NodeHandle, NodeType, Dropdown, NordunetUniqueId


class NordunetFormTest(NeoTestCase):

    def test_new_cable_form_duplicate(self):
        cable_type = NodeType.objects.create(type='Cable', slug='cable')
        dropdown = Dropdown.objects.get(name='cable_types')
        dropdown.choice_set.create(name='LC', value='LC')
        NordunetUniqueId.objects.create(unique_id='cable1')

        NodeHandle.objects.create(
            node_name='cable1',
            node_type=cable_type,
            node_meta_type='Physical',
            creator_id=1,
            modifier_id=1)

        form_data = {
            'name': 'cable1',
            'cable_type': 'LC',
        }
        form = forms.NewCableForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('cable1 already in', form.errors['name'][0])
