# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, NodeType
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
