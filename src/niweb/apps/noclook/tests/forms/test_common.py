# -*- coding: utf-8 -*-
from ..neo4j_base import NeoTestCase
from apps.noclook.forms import common as forms
from apps.noclook.models import NodeHandle, NodeType, Dropdown, NordunetUniqueId


class CommonFormTest(NeoTestCase):

    def test_new_organization(self):
        test_org_id = '5678'
        # create a test organization
        self.organization1 = self.create_node('organization1', 'organization', meta='Logical')

        # add an organization_id
        organization1_data = {
            'organization_id': test_org_id,
        }

        for key, value in organization1_data.items():
            self.organization1.get_node().add_property(key, value)

        data1 = {
            'account_id': '1234',
            'name': 'Lipsum',
            'description': 'Lorem ipsum dolor sit amet, \
                            consectetur adipiscing elit.\
                            Morbi dignissim vehicula \
                            justo sit amet pulvinar. \
                            Fusce ipsum nulla, feugiat eu\
                            gravida eget, efficitur a risus.',
            'website': 'www.lipsum.com',
            'organization_id': test_org_id,
            'type': 'university_college',
            'incident_management_info': 'They have a form on their website',
        }

        form = forms.NewOrganizationForm(data=data1)
        self.assertFalse(form.is_valid())
