# -*- coding: utf-8 -*-

__author__ = 'ffuentes'

from collections import OrderedDict
from faker import Faker
from apps.nerds.lib.consumer_util import get_user
from apps.noclook import helpers
from apps.noclook.models import NodeHandle, NodeType, Dropdown, Choice, NodeHandleContext
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
import norduniclient as nc
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

        self.user = get_user()

    def escape_quotes(self, str_in):
        return str_in.replace("'", "\'")

    def company_name(self):
        return self.escape_quotes( self.fake.company() )

    def first_name(self):
        return self.escape_quotes( self.fake.first_name() )

    def last_name(self):
        return self.escape_quotes( self.fake.last_name() )

    def rand_person_or_company_name(self):
        person_name = '{} {}'.format(self.first_name(), self.last_name())
        company_name = self.company_name()
        name = random.choice((person_name, company_name))

        return name

    @staticmethod
    def clean_rogue_nodetype():
        NodeType.objects.filter(type="").delete()

    def get_or_create_node(self, node_name, type_name, meta_type):
        node_type = NetworkFakeDataGenerator.get_nodetype(type_name)

        # create object
        nh = NodeHandle.objects.get_or_create(
            node_name=node_name,
            node_type=node_type,
            node_meta_type=meta_type,
            creator=self.user,
            modifier=self.user
        )[0]

        return nh

    def create_entity(self, data_f=None, type_name=None, metatype=None, \
                        name_alias=None, name=None):
        data = data_f()
        name_key = 'name' if not name_alias else name_alias

        if not name:
            name = data.get(name_key, None)

        nh = self.get_or_create_node(
            name, type_name, metatype) # Logical

        # add context
        self.add_community_context(nh)

        for key, value in data.items():
            value = self.escape_quotes(value)
            nh.get_node().add_property(key, value)

        return nh


class CommunityFakeDataGenerator(FakeDataGenerator):
    def add_community_context(self, nh):
        com_ctx = sriutils.get_community_context()
        NodeHandleContext(nodehandle=nh, context=com_ctx).save()

    def create_fake_contact(self):
        salutations = ['Ms.', 'Mr.', 'Dr.', 'Mrs.', 'Mx.']
        contact_types_drop = Dropdown.objects.get(name='contact_type')
        contact_types = Choice.objects.filter(dropdown=contact_types_drop)
        contact_types = [x.value for x in contact_types]

        contact_dict = {
            'salutation': random.choice(salutations),
            'first_name': self.first_name(),
            'last_name': self.last_name(),
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
        organization_name = self.company_name()
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

    def create_fake_procedure(self):
        procedure_dict = {
            'name': self.fake.sentence(),
            'description': self.fake.paragraph(),
        }

        return procedure_dict

    def create_group(self, name=None):
        return self.create_entity(
            data_f=self.create_fake_group,
            type_name='Group',
            metatype=META_TYPES[1], # Logical
            name=name,
        )

    def create_procedure(self):
        return self.create_entity(
            data_f=self.create_fake_procedure,
            type_name='Procedure',
            metatype=META_TYPES[1], # Logical
        )

    def create_organization(self, name=None):
        return self.create_entity(
            data_f=self.create_fake_organization,
            type_name='Organization',
            metatype=META_TYPES[2], # Relation
            name_alias='account_name',
            name=name,
        )


class NetworkFakeDataGenerator(FakeDataGenerator):
    def __init__(self, seed=None):
        super().__init__()

        # set vars
        self.max_cable_providers = 5
        self.max_ports_total = 40

    def add_network_context(self, nh):
        net_ctx = sriutils.get_network_context()
        NodeHandleContext(nodehandle=nh, context=net_ctx).save()

    def get_port_name(self):
        return str(random.randint(0, 50000))

    @staticmethod
    def get_nodetype(type_name):
        return NodeType.objects.get_or_create(type=type_name, slug=slugify(type_name))[0]

    def get_dropdown_keys(self, dropdown_name):
        return [ x[0] for x in Dropdown.get(dropdown_name).as_choices()[1:] ]

    ## Organizations
    def create_customer(self, name=None):
        # create object
        if not name:
            name = self.rand_person_or_company_name()

        customer = self.get_or_create_node(
            name, 'Customer', META_TYPES[2]) # Relation

        # add context
        self.add_network_context(customer)

        data = {
            'url': self.fake.url(),
            'description': self.fake.paragraph(),
        }

        for key, value in data.items():
            customer.get_node().add_property(key, value)

        return customer

    def create_end_user(self, name=None):
        # create object
        if not name:
            name = self.rand_person_or_company_name()

        name = self.rand_person_or_company_name()
        enduser = self.get_or_create_node(
            name, 'End User', META_TYPES[2]) # Relation

        # add context
        self.add_network_context(enduser)

        data = {
            'url': self.fake.url(),
            'description': self.fake.paragraph(),
        }

        for key, value in data.items():
            enduser.get_node().add_property(key, value)

        return enduser

    def create_peering_partner(self, name=None):
        # create object
        if not name:
            name = self.company_name()

        peering_partner = self.get_or_create_node(
            name, 'Peering Partner', META_TYPES[2]) # Relation

        data = {
            'as_number' : str(random.randint(0, 99999)).zfill(5),
        }

        for key, value in data.items():
            peering_partner.get_node().add_property(key, value)

        # add context
        self.add_network_context(peering_partner)

        return peering_partner

    def create_peering_group(self, name=None):
        # create object
        if not name:
            name = self.company_name()

        name = self.company_name()
        peering_group = self.get_or_create_node(
            name, 'Peering Group', META_TYPES[1]) # Logical

        # add context
        self.add_network_context(peering_group)

        # add random dependents
        num_dependencies = random.randint(1, 3)

        for i in range(0, num_dependencies):
            dependency = random.choice([
                self.create_host,
            ])
            dependency = dependency()
            rel_maker = PhysicalLogicalDataRelationMaker()
            rel_maker.add_dependency(self.user, peering_group, dependency)

        return peering_group

    def create_provider(self, name=None):
        if not name:
            name = self.company_name()

        provider = self.get_or_create_node(
            name, 'Provider', META_TYPES[2]) # Relation

        # add context
        self.add_network_context(provider)

        data = {
            'url' : self.fake.url(),
            'description': self.fake.paragraph(),
        }

        for key, value in data.items():
            provider.get_node().add_property(key, value)

        return provider

    def create_site_owner(self, name=None):
        # create object
        if not name:
            name = self.rand_person_or_company_name()

        siteowner = self.get_or_create_node(
            name, 'Site Owner', META_TYPES[2]) # Relation

        # add context
        self.add_network_context(siteowner)

        data = {
            'url': self.fake.url(),
            'description': self.fake.paragraph(),
        }

        for key, value in data.items():
            siteowner.get_node().add_property(key, value)

        return siteowner

    ## Equipment and cables

    def create_port(self, name=None):
        if not name:
            name = self.get_port_name()

        # create object
        port = self.get_or_create_node(
            name, 'Port', META_TYPES[0]) # Physical

        # add context
        self.add_network_context(port)

        # add data
        port_types = self.get_dropdown_keys('port_types')

        data = {
            'port_type' : random.choice(port_types),
            'description' : self.fake.paragraph(),
            #'relationship_parent' : None, # not used for the moment
        }

        for key, value in data.items():
            port.get_node().add_property(key, value)

        return port

    def create_cable(self, name=None):
        # create object
        if not name:
            name = self.fake.hostname()

        cable = self.get_or_create_node(
            self.fake.hostname(), 'Cable', META_TYPES[0]) # Physical

        # add context
        self.add_network_context(cable)

        # add data
        cable_types = self.get_dropdown_keys('cable_types')

        # check if there's any provider or if we should create one
        provider_type = NetworkFakeDataGenerator.get_nodetype('Provider')
        providers = NodeHandle.objects.filter(node_type=provider_type)

        max_providers = self.max_cable_providers
        provider = None

        if not providers or len(providers) < max_providers:
            provider = self.create_provider()
        else:
            provider = random.choice(list(providers))

        # add ports
        port_a = None
        port_b = None

        port_type = NetworkFakeDataGenerator.get_nodetype('Port')
        total_ports = NodeHandle.objects.filter(node_type=port_type).count()

        if total_ports < self.max_ports_total:
            port_a = self.create_port()
            port_b = self.create_port()
        else:
            all_ports = list(NodeHandle.objects.filter(node_type=port_type))
            port_a = random.choice(all_ports)
            port_b = random.choice(all_ports)


        data = {
            'cable_type' : random.choice(cable_types),
            'description' : self.fake.paragraph(),
            'relationship_provider' : provider.handle_id,
            'relationship_end_a' : port_a.handle_id,
            'relationship_end_b' : port_b.handle_id,
        }

        for key, value in data.items():
            cable.get_node().add_property(key, value)

        # add relationship to provider
        helpers.set_provider(self.user, cable.get_node(), provider.handle_id)
        helpers.set_connected_to(self.user, cable.get_node(), port_a.handle_id)
        helpers.set_connected_to(self.user, cable.get_node(), port_b.handle_id)

        return cable

    def create_host(self, name=None, type_name="Host", metatype=META_TYPES[1]):
        # create object
        if not name:
            name = self.escape_quotes(self.fake.hostname())

        host = self.get_or_create_node(
            name, type_name, metatype)

        # add context
        self.add_network_context(host)

        # add data
        num_ips = random.randint(0,4)
        ip_adresses = [self.fake.ipv4()]

        for i in range(num_ips):
            ip_adresses.append(self.fake.ipv4())

        operational_states = self.get_dropdown_keys('operational_states')
        managed_by = self.get_dropdown_keys('host_management_sw')
        responsible_group = self.get_dropdown_keys('responsible_groups')
        support_group = self.get_dropdown_keys('responsible_groups')
        backup_systems = ['TSM', 'IP nett']
        security_class = self.get_dropdown_keys('security_classes')
        os_options = (
            ('GNU/Linux', ('Ubuntu', 'Debian', 'Fedora', 'Arch')),
            ('Microsoft Windows', ('8', '10', 'X'))
        )
        os_choice = random.choice(os_options)

        data = {
            'ip_addresses' : ip_adresses,
            'rack_units': random.randint(1,10),
            'rack_position': random.randint(1,10),
            'description': self.escape_quotes(self.fake.paragraph()),
            'operational_state': random.choice(operational_states),
            'managed_by': random.choice(managed_by),
            'responsible_group': random.choice(responsible_group),
            'support_group': random.choice(support_group),
            'backup': random.choice(backup_systems),
            'security_class': random.choice(security_class),
            'security_comment':self.escape_quotes(self.fake.paragraph()),
            'os': os_choice[0],
            'os_version': random.choice(os_choice[1]),
            'model': self.escape_quotes(self.fake.license_plate()),
            'vendor': self.company_name(),
            'service_tag': self.escape_quotes(self.fake.license_plate()),
        }

        for key, value in data.items():
            host.get_node().add_property(key, value)

        return host

    def create_router(self, name=None):
        # create object
        if not name:
            name = '{}-{}'.format(
                self.fake.safe_color_name(), self.fake.ean8())

        router = self.get_or_create_node(
            name, 'Router', META_TYPES[0])

        # add context
        self.add_network_context(router)

        # add data
        operational_states = self.get_dropdown_keys('operational_states')

        data = {
            'rack_units': random.randint(1,10),
            'rack_position': random.randint(1,10),
            'operational_state': random.choice(operational_states),
            'description': self.fake.paragraph(),
            'model': self.fake.license_plate(),
            'version': '{}.{}'.format(random.randint(0,20), random.randint(0,99)),
        }

        for key, value in data.items():
            router.get_node().add_property(key, value)

        return router

    def create_switch(self, name=None):
        # create object
        if not name:
            name = '{}-{}'.format(
                self.fake.safe_color_name(), self.fake.ean8())

        switch = self.create_host(name, "Switch", metatype=META_TYPES[0])

        data = {
            'max_number_of_ports': random.randint(5,25),
        }

        for key, value in data.items():
            switch.get_node().add_property(key, value)

        return switch

    def create_firewall(self, name=None):
        # create object
        if not name:
            name = '{}-{}'.format(
                self.fake.safe_color_name(), self.fake.ean8())

        firewall = self.create_host(name, "Firewall", metatype=META_TYPES[0])

        data = {
            'max_number_of_ports': random.randint(5,25),
        }

        for key, value in data.items():
            firewall.get_node().add_property(key, value)

        return firewall

    def create_host_user(self, name=None):
        # create object
        if not name:
            name = self.rand_person_or_company_name()

        name = self.rand_person_or_company_name()
        hostuser = self.get_or_create_node(
            name, 'Host User', META_TYPES[2]) # Relation

        # add context
        self.add_network_context(hostuser)

        data = {
            'url': self.fake.url(),
            'description': self.fake.paragraph(),
        }

        for key, value in data.items():
            hostuser.get_node().add_property(key, value)

        return hostuser

    def create_optical_node(self, name=None):
        if not name:
            name = '{}-{}'.format(
                self.fake.safe_color_name(), self.fake.ean8())

        onode = self.get_or_create_node(
            name, 'Optical Node', META_TYPES[0])

        # add context
        self.add_network_context(onode)

        # add data
        operational_states = self.get_dropdown_keys('operational_states')
        types = self.get_dropdown_keys('optical_node_types')

        data = {
            'operational_state': random.choice(operational_states),
            'type': random.choice(types),
            'description': self.fake.paragraph(),
            'rack_units': random.randint(1,10),
            'rack_position': random.randint(1,10),
            'rack_back': bool(random.getrandbits(1)),
        }

        for key, value in data.items():
            router.get_node().add_property(key, value)

        return router


class DataRelationMaker:
    def __init__(self):
        self.user = get_user()


class PhysicalLogicalDataRelationMaker(DataRelationMaker):
    def add_dependency(cls, user, main_logical_nh, dep_logical_nh):
        main_logical_nh = main_logical_nh.get_node()
        dep_logical_handle_id = dep_logical_nh.handle_id
        helpers.set_depends_on(user, main_logical_nh, dep_logical_handle_id)


class LogicalDataRelationMaker(DataRelationMaker):
    def add_part_of(self, user, logical_nh, physical_nh):
        physical_node = physical_nh.get_node()
        logical_handle_id = logical_nh.handle_id
        helpers.set_part_of(user, physical_node, logical_handle_id)

    def add_dependent(self, user, main_logical_nh, dep_logical_nh):
        main_logical_handle_id = main_logical_nh.handle_id
        dep_logical_nh = dep_logical_nh.get_node()
        helpers.set_depends_on(user, dep_logical_nh, main_logical_handle_id)


class RelationDataRelationMaker(DataRelationMaker):
    def add_provides(self, user, relation_nh, phylogical_nh):
        the_node = phylogical_nh.get_node()
        relation_handle_id = relation_nh.handle_id
        helpers.set_provider(user, the_node, relation_handle_id)

    def add_owns(self, user, relation_nh, physical_nh):
        physical_node = physical_nh.get_node()
        relation_handle_id = relation_nh.handle_id
        helpers.set_owner(user, physical_node, relation_handle_id)

    def add_responsible_for(self, user, relation_nh, location_nh):
        location_node = location_nh.get_node()
        relation_handle_id = relation_nh.handle_id
        helpers.set_responsible_for(user, location_node, relation_handle_id)


class PhysicalDataRelationMaker(DataRelationMaker):
    def add_parent(self, user, physical_nh, physical_parent_nh):
        handle_id = physical_nh.handle_id
        parent_handle_id = physical_parent_nh.handle_id

        q = """
            MATCH   (n:Node:Physical {handle_id: {handle_id}}),
                    (p:Node:Physical {handle_id: {parent_handle_id}})
            MERGE (n)<-[r:Has]-(p)
            RETURN n, r, p
            """

        result = nc.query_to_dict(nc.graphdb.manager, q,
                        handle_id=handle_id, parent_handle_id=parent_handle_id)
