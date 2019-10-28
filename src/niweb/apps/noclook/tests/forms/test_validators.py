# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, NodeType
from apps.noclook.forms import common as forms
from apps.noclook.forms.validators import validate_organization, \
                                            validate_contact, validate_group, \
                                            validate_procedure
from django.core.exceptions import ValidationError
from ..neo4j_base import NeoTestCase

class Neo4jGraphQLTest(NeoTestCase):
    def test_validators(self):
        # create nodes
        self.organization1 = self.create_node('organization1', 'organization', meta='Logical')
        self.contact1 = self.create_node('contact1', 'contact', meta='Relation')
        self.group1 = self.create_node('group1', 'group', meta='Logical')
        self.procedure1 = self.create_node('procedure1', 'procedure', meta='Logical')

        # organization
        # test valid organization
        valid = True

        try:
            validate_organization(self.organization1.handle_id)
        except ValidationError:
            valid = False

        self.assertTrue(valid)

        # test a non valid organization (a contact for example)
        valid = True

        try:
            validate_organization(self.contact1.handle_id)
        except ValidationError:
            valid = False

        self.assertFalse(valid)

        # contact
        # test valid contact
        valid = True

        try:
            validate_contact(self.contact1.handle_id)
        except ValidationError:
            valid = False

        self.assertTrue(valid)

        # test a non valid contact (a organization for example)
        valid = True

        try:
            validate_contact(self.organization1.handle_id)
        except ValidationError:
            valid = False

        self.assertFalse(valid)

        # group
        # test valid group
        valid = True

        try:
            validate_group(self.group1.handle_id)
        except ValidationError:
            valid = False

        self.assertTrue(valid)

        # test a non valid group (a organization for example)
        valid = True

        try:
            validate_group(self.organization1.handle_id)
        except ValidationError:
            valid = False

        self.assertFalse(valid)

    def test_forms(self):
        # create nodes
        self.organization1 = self.create_node('organization1', 'organization', meta='Logical')
        self.contact1 = self.create_node('contact1', 'contact', meta='Relation')
        self.group1 = self.create_node('group1', 'group', meta='Logical')
        self.procedure1 = self.create_node('procedure1', 'procedure', meta='Logical')

        ## organization
        data = {
            'handle_id': self.organization1.handle_id,
            'account_id': '1234',
            'name': 'Lipsum',
            'description': 'Lorem ipsum dolor sit amet, \
                            consectetur adipiscing elit.\
                            Morbi dignissim vehicula \
                            justo sit amet pulvinar. \
                            Fusce ipsum nulla, feugiat eu\
                            gravida eget, efficitur a risus.',
            'website': 'www.lipsum.com',
            'customer_id': '5678',
            'type': 'provider',
            'incident_management_info': 'They have a form on their website',
            'relationship_parent_of': self.organization1.handle_id,
        }

        # check a valid form
        form = forms.EditOrganizationForm(data)
        self.assertTrue(form.is_valid())

        # check a non valid form
        data['relationship_parent_of'] = self.contact1.handle_id
        form = forms.EditOrganizationForm(data)
        self.assertFalse(form.is_valid())

        ## contact
        data = {
            'handle_id': self.contact1.handle_id,
            'first_name': 'Alice',
            'last_name': 'Svensson',
            'contact_type': 'person',
            'title': 'PhD',
            'pgp_fingerprint': '-',
            'relationship_works_for': self.organization1.handle_id,
            'relationship_member_of': self.group1.handle_id,
        }

        # check a valid form
        form = forms.EditContactForm(data)
        self.assertTrue(form.is_valid())

        # check a non valid form
        data['relationship_member_of'] = self.contact1.handle_id
        form = forms.EditContactForm(data)
        self.assertFalse(form.is_valid())

        ## group
        data = {
            'handle_id': self.group1.handle_id,
            'name': 'Text providers',
            'description': 'Lorem ipsum dolor sit amet, \
                            consectetur adipiscing elit.\
                            Morbi dignissim vehicula \
                            justo sit amet pulvinar. \
                            Fusce ipsum nulla, feugiat eu\
                            gravida eget, efficitur a risus.',
            'relationship_member_of': self.contact1.handle_id,
        }

        # check a valid form
        form = forms.EditGroupForm(data)
        self.assertTrue(form.is_valid())

        # check a non valid form
        data['relationship_member_of'] = self.group1.handle_id
        form = forms.EditGroupForm(data)
        self.assertFalse(form.is_valid())
