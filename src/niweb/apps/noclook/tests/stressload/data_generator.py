# -*- coding: utf-8 -*-

__author__ = 'ffuentes'

from collections import OrderedDict
from faker import Faker
from apps.nerds.lib.consumer_util import get_user
from apps.noclook.models import NodeHandle, NodeType, Dropdown, Choice, NodeHandleContext
from django.contrib.auth.models import User
from norduniclient import META_TYPES

import apps.noclook.vakt.utils as sriutils
import random

class FakeDataGenerator:
    def __init__(self, seed=None):
        locales = OrderedDict([
            ('en_GB', 1),
            ('sv_SE', 2),
        ])
        self.fake = Faker(locales)

        if seed:
            self.fake.seed_instance(seed)

    def create_fake_contact(self):
        salutations = ['Ms.', 'Mr.', 'Dr.', 'Mrs.', 'Mx.']
        contact_types_drop = Dropdown.objects.get(name='contact_type')
        contact_types = Choice.objects.filter(dropdown=contact_types_drop)
        contact_types = [x.value for x in contact_types]

        contact_dict = {
            'salutation': random.choice(salutations),
            'first_name': self.fake.first_name(),
            'last_name': self.fake.last_name(),
            'title': '',
            'contact_role': self.fake.job(),
            'contact_type': random.choice(contact_types),
            'mailing_street': self.fake.address().replace('\n', ' '),
            'mailing_city': self.fake.city(),
            'mailing_zip': self.fake.postcode(),
            'mailing_state': self.fake.state(),
            'mailing_country': self.fake.country(),
            'phone': self.fake.phone_number(),
            'mobile': self.fake.phone_number(),
            'fax': self.fake.phone_number(),
            'email': self.fake.ascii_company_email(),
            'other_email': self.fake.ascii_company_email(),
            'PGP_fingerprint': self.fake.sha256(False),
            'account_name': '',
        }

        return contact_dict

    def create_fake_organization(self):
        organization_name = self.fake.company()
        organization_id = organization_name.upper()

        org_types_drop = Dropdown.objects.get(name='organization_types')
        org_types = Choice.objects.filter(dropdown=org_types_drop)
        org_types = [x.value for x in org_types]

        organization_dict = {
            'organization_number': '',
            'account_name': organization_name,
            'description': self.fake.catch_phrase(),
            'phone': self.fake.phone_number(),
            'website': self.fake.url(),
            'organization_id': organization_id,
            'type': random.choice(org_types),
            'parent_account': '',
        }

        return organization_dict

    def create_fake_group(self):
        group_dict = {
            'name': self.fake.sentence(),
            'description': self.fake.paragraph(),
        }

        return group_dict


class NetworkFakeDataGenerator:
    def __init__(self, seed=None):
        locales = OrderedDict([
            ('en_GB', 1),
            ('sv_SE', 2),
        ])
        self.fake = Faker(locales)

        if seed:
            self.fake.seed_instance(seed)

        self.user = user = get_user()

    def add_network_context(self, nh):
        net_ctx = sriutils.get_network_context()
        NodeHandleContext(nodehandle=nh, context=net_ctx).save()

    def create_provider(self):
        type = NodeType.objects.get_or_create(type='Provider', slug='provider')[0]

        # create object
        provider = NodeHandle.objects.get_or_create(
            node_name=self.fake.company(),
            node_type=type,
            node_meta_type=META_TYPES[0],
            creator=self.user,
            modifier=self.user
        )[0]

        # add context
        self.add_network_context(provider)

        data = {
            'url' : self.fake.url(),
        }

        for key, value in data.items():
            provider.get_node().add_property(key, value)

        return provider

    def create_cable(self):
        type = NodeType.objects.get_or_create(type='Cable', slug='cable')[0]

        # create object
        cable = NodeHandle.objects.get_or_create(
            node_name=self.fake.hostname(),
            node_type=type,
            node_meta_type=META_TYPES[0],
            creator=self.user,
            modifier=self.user
        )[0]

        # add context
        self.add_network_context(cable)

        # add data
        cable_types = [ x[0] for x in Dropdown.get('cable_types').as_choices()[1:] ]

        # check if there's any provider or if we should create one
        provider_type = NodeType.objects.get_or_create(type='Provider', slug='provider')[0]
        providers = NodeHandle.objects.filter(node_type=provider_type)

        max_providers = 5
        provider = None

        if not providers or len(providers) < max_providers:
            provider = self.create_provider()
        else:
            provider = random.choice(list(providers))

        data = {
            'cable_type' : random.choice(cable_types),
            'description' : self.fake.paragraph(),
            'relationship_provider' : provider.handle_id,
        }

        for key, value in data.items():
            cable.get_node().add_property(key, value)

        return cable
