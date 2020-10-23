# -*- coding: utf-8 -*-

__author__ = 'ffuentes'

from collections import OrderedDict
from faker import Faker
from apps.nerds.lib.consumer_util import get_user
from apps.noclook import helpers, unique_ids
from apps.noclook.forms import NewServiceForm
from apps.noclook.models import NodeHandle, NodeType, Dropdown as DropModel, \
                                Choice, NodeHandleContext, UniqueIdGenerator, \
                                NordunetUniqueId, ServiceType
from apps.noclook.schema.utils import sunet_forms_enabled
from django.contrib.auth.models import User
from django.core.management import call_command
from django.template.defaultfilters import slugify
from dynamic_preferences.registries import global_preferences_registry
import norduniclient as nc
from norduniclient import META_TYPES

import apps.noclook.vakt.utils as sriutils
import random
import string
import os

class FakeDataGenerator:
    counties = [
        'Blekinge', 'Dalarna', 'Gotland', 'Gävleborg', 'Halland', 'Jämtland',
        'Jönköping', 'Kalmar', 'Kronoberg', 'Norrbotten', 'Skåne', 'Halland',
        'Västra Götaland', 'Värmland', 'Örebro', 'Västmanland', 'Dalarna',
        'Gävleborg', 'Västernorrland', 'Jämtland,'
    ]

    def __init__(self, seed=None):
        locales = OrderedDict([
            ('en_GB', 1),
            ('sv_SE', 2),
        ])
        self.fake = Faker(locales)

        if seed:
            self.fake.seed_instance(seed)

        self.user = get_user()

    def add_community_context(self, nh):
        com_ctx = sriutils.get_community_context()
        NodeHandleContext(nodehandle=nh, context=com_ctx).save()

    def add_network_context(self, nh):
        net_ctx = sriutils.get_network_context()
        NodeHandleContext(nodehandle=nh, context=net_ctx).save()

    def escape_quotes(self, str_in):
        out = str_in

        try:
            out = str_in.replace("'", "`")
        except AttributeError:
            pass

        return out

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

        name = self.escape_quotes(name)

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
            name, type_name, metatype)

        # add context
        self.add_community_context(nh)

        for key, value in data.items():
            value = self.escape_quotes(value)
            nh.get_node().add_property(key, value)

        return nh


    def create_address(self, name=None, context_f=None):
        # create object
        if not name:
            name = self.rand_person_or_company_name()

        address = self.get_or_create_node(
            name, 'Address', META_TYPES[1]) # Logical

        if not context_f:
            context_f = self.add_community_context

        # add context
        context_f(address)

        data = {
            'phone': self.fake.phone_number(),
            'street': self.fake.street_address(),
            'floor': str(random.randint(1,12)),
            'room': '{}{}'.format(random.randint(1,20), \
                                    random.choice(string.ascii_letters).upper()),
            'postal_code': self.fake.postcode(),
            'postal_area': self.fake.country_code(),
        }

        for key, value in data.items():
            value = self.escape_quotes(value)
            address.get_node().add_property(key, value)

        return address

    def random_county(self):
        return random.choice(self.counties)


class CommunityFakeDataGenerator(FakeDataGenerator):
    def create_fake_contact(self):
        salutations = ['Ms.', 'Mr.', 'Dr.', 'Mrs.', 'Mx.']
        contact_types_drop = DropModel.objects.get(name='contact_type')
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

        org_types_drop = DropModel.objects.get(name='organization_types')
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
            'name': self.fake.job(),
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
        organization = self.create_entity(
            data_f=self.create_fake_organization,
            type_name='Organization',
            metatype=META_TYPES[2], # Relation
            name_alias='account_name',
            name=name,
        )

        num_address = random.randint(1, 3)

        for i in range(num_address):
            address = self.create_address()
            helpers.add_address_organization(self.user, address, organization.handle_id)

        return organization


class NetworkFakeDataGenerator(FakeDataGenerator):
    def __init__(self, seed=None):
        super().__init__()

        # set vars
        self.max_cable_providers = 5
        self.max_ports_total = 40

        self.optical_path_dependency_types = {
            'ODF': self.create_odf,
            'OpticalLink': self.create_optical_link,
            'OpticalMultiplexSection': self.create_optical_multiplex_section,
            'OpticalNode': self.create_optical_node,
            'Router': self.create_router,
            'Switch': self.create_switch,
            'OpticalPath': self.create_optical_path,
            'Service': self.create_service
        }

        self.service_dependency_types = {
            'Host': self.create_host,
            'Firewall': self.create_firewall,
            'ODF': self.create_odf,
            'OpticalNode': self.create_optical_node,
            'OpticalPath': self.create_optical_path,
            'OpticalLink': self.create_optical_link,
            #'OpticalFilter': self.create_optical_filter,
            'Router': self.create_router,
            'Service': self.create_service,
            'Switch': self.create_switch,
            #'ExternalEquipment': self.create_external_equipment,
        }

        self.service_user_categories = {
            'Customer': self.create_customer,
            'EndUser': self.create_end_user,
        }

    def get_port_name(self):
        return str(random.randint(0, 50000))

    @staticmethod
    def get_nodetype(type_name):
        return NodeType.objects.get_or_create(type=type_name, slug=slugify(type_name))[0]

    def get_dropdown_keys(self, dropdown_name):
        return [ x[0] for x in DropModel.get(dropdown_name).as_choices()[1:] ]

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
            value = self.escape_quotes(value)
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
            value = self.escape_quotes(value)
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
            value = self.escape_quotes(value)
            peering_partner.get_node().add_property(key, value)

        # add context
        self.add_network_context(peering_partner)

        return peering_partner

    def create_unit(self, name=None):
        # create object
        if not name:
            name = self.fake.isbn10()

        unit = self.get_or_create_node(
            name, 'Unit', META_TYPES[1]) # Logical

        # add data
        num_ips = random.randint(0,4)
        ip_addresses = [self.fake.ipv4()]

        for i in range(num_ips):
            ip_addresses.append(self.fake.ipv4())

        data = {
            'description' : self.fake.paragraph(),
            'vlan' : self.fake.ipv4(),
            'ip_addresses': ip_addresses,
        }

        for key, value in data.items():
            value = self.escape_quotes(value)
            unit.get_node().add_property(key, value)

        # add context
        self.add_network_context(unit)

        return unit


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
        num_dependencies = random.randint(2, 4)
        rel_maker = LogicalDataRelationMaker()

        unit_ips = []

        for i in range(0, num_dependencies):
            unit = self.create_unit()
            unit_ip = self.fake.ipv4()
            unit_ips.append(unit_ip)

            # get an existent router or add one
            router = self.create_router(add_ports=True)

            # get a port from the router
            ports = router.get_node().get_ports()
            port = NodeHandle.objects.get(handle_id=\
                random.choice(ports['Has'])['node'].handle_id)

            rel_maker.add_part_of(self.user, unit, port)

            # add dependency
            peering_group.get_node().set_group_dependency(
                unit.handle_id, unit_ip
            )

        # add random peering partners
        num_dependencies = random.randint(0, 3)
        ppartner_type = NetworkFakeDataGenerator.get_nodetype('Peering Partner')
        all_ppartners = NodeHandle.objects.filter(node_type=ppartner_type)
        all_ppartners = list(all_ppartners)
        ppartners = []

        for i in range(num_dependencies):
            if all_ppartners:
                ppartner = random.choice(all_ppartners)
                all_ppartners.remove(ppartner)
                ppartners.append(ppartner)
            else:
                ppartner = self.create_peering_partner()
                ppartners.append(ppartner)

        for ppartner in ppartners:
            ppartner_node = ppartner.get_node()
            ip = self.fake.ipv4()
            if unit_ips:
                ip = random.choice(unit_ips)

            ppartner_node.set_peering_group(peering_group.handle_id,
                                            ip)

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
            value = self.escape_quotes(value)
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
            value = self.escape_quotes(value)
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
            value = self.escape_quotes(value)
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
            'description' : self.escape_quotes(self.fake.paragraph()),
            'relationship_provider' : provider.handle_id,
            'relationship_end_a' : port_a.handle_id,
            'relationship_end_b' : port_b.handle_id,
        }

        if sunet_forms_enabled():
            cable_contract = random.choice(
                Dropdown.objects.get(name="tele2_cable_contracts").as_choices()[1:][1]
            )
            data['tele2_cable_contract'] = cable_contract
            data['tele2_alternative_circuit_id'] = self.escape_quotes(self.fake.ean8()),


        for key, value in data.items():
            value = self.escape_quotes(value)
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
            value = self.escape_quotes(value)
            host.get_node().add_property(key, value)

        return host

    def create_router(self, name=None, add_ports=False):
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
            value = self.escape_quotes(value)
            router.get_node().add_property(key, value)

        # add ports
        if add_ports:
            num_ports = random.randint(1, 5) # rather small but fine for our purpose
            relation_maker = PhysicalDataRelationMaker()

            for i in range(num_ports):
                port = self.create_port()
                relation_maker.add_has(self.user, router, port)

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
            value = self.escape_quotes(value)
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
            value = self.escape_quotes(value)
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
            value = self.escape_quotes(value)
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
            value = self.escape_quotes(value)
            onode.get_node().add_property(key, value)

        return onode

    def create_odf(self, name=None):
        # create object
        if not name:
            name = '{}-{}'.format(
                self.fake.safe_color_name(), self.fake.ean8())

        odf = self.get_or_create_node(
            name, 'ODF', META_TYPES[0])

        # add context
        self.add_network_context(odf)

        # add data
        operational_states = self.get_dropdown_keys('operational_states')

        data = {
            'rack_units': random.randint(1,10),
            'rack_position': random.randint(1,10),
            'rack_back': bool(random.getrandbits(1)),
            'operational_state': random.choice(operational_states),
            'description': self.fake.paragraph(),
            'max_number_of_ports': random.randint(5,25),
        }

        for key, value in data.items():
            value = self.escape_quotes(value)
            odf.get_node().add_property(key, value)

        return odf

    def create_optical_link(self, name=None):
        # create object
        if not name:
            name = '{}-{}'.format(
                self.fake.ean8(), self.escape_quotes(self.fake.license_plate()))

        optical_link = self.get_or_create_node(
            name, 'Optical Link', META_TYPES[1])

        # add context
        self.add_network_context(optical_link)

        # check if there's any provider or if we should create one
        provider_type = NetworkFakeDataGenerator.get_nodetype('Provider')
        providers = NodeHandle.objects.filter(node_type=provider_type)

        max_providers = self.max_cable_providers
        provider = None

        if not providers or len(providers) < max_providers:
            provider = self.create_provider()
        else:
            provider = random.choice(list(providers))

        # add data
        link_types = self.get_dropdown_keys('optical_link_types')
        interface_types = self.get_dropdown_keys('optical_link_interface_type')
        operational_states = self.get_dropdown_keys('operational_states')

        data = {
            'description': self.fake.paragraph(),
            'link_type': random.choice(link_types),
            'interface_type': random.choice(interface_types),
            'operational_state': random.choice(operational_states),
            'relationship_provider' : provider.handle_id,
        }

        for key, value in data.items():
            value = self.escape_quotes(value)
            optical_link.get_node().add_property(key, value)

        helpers.set_provider(self.user,
            optical_link.get_node(), provider.handle_id)

        # add random ports
        num_ports = random.randint(1, 3)

        for i in range(0, num_ports):
            port = self.create_port()
            rel_maker = PhysicalLogicalDataRelationMaker()
            rel_maker.add_dependency(self.user, optical_link, port)

        return optical_link

    def create_optical_multiplex_section(self, name=None):
        # create object
        if not name:
            name = '{}-{}'.format(
                self.escape_quotes(self.fake.license_plate()), self.fake.ean8())

        optical_multisection = self.get_or_create_node(
            name, 'Optical Multiplex Section', META_TYPES[1])

        # add context
        self.add_network_context(optical_multisection)

        # check if there's any provider or if we should create one
        provider_type = NetworkFakeDataGenerator.get_nodetype('Provider')
        providers = NodeHandle.objects.filter(node_type=provider_type)

        max_providers = self.max_cable_providers
        provider = None

        if not providers or len(providers) < max_providers:
            provider = self.create_provider()
        else:
            provider = random.choice(list(providers))

        # add data
        link_types = self.get_dropdown_keys('optical_link_types')
        interface_types = self.get_dropdown_keys('optical_link_interface_type')
        operational_states = self.get_dropdown_keys('operational_states')

        data = {
            'description': self.fake.paragraph(),
            'operational_state': random.choice(operational_states),
            'relationship_provider' : provider.handle_id,
        }

        for key, value in data.items():
            value = self.escape_quotes(value)
            optical_multisection.get_node().add_property(key, value)

        helpers.set_provider(self.user,
            optical_multisection.get_node(), provider.handle_id)

        # add random ports
        num_ports = random.randint(1, 3)

        for i in range(0, num_ports):
            port = self.create_port()
            rel_maker = PhysicalLogicalDataRelationMaker()
            rel_maker.add_dependency(self.user, optical_multisection, port)

        return optical_multisection


    def create_optical_path(self, name=None):
        # create object
        if not name:
            name = '{}-{}'.format(
                self.fake.ean8(), self.escape_quotes(self.fake.license_plate()))

        optical_path = self.get_or_create_node(
            name, 'Optical Path', META_TYPES[1])

        # add context
        self.add_network_context(optical_path)

        # check if there's any provider or if we should create one
        provider_type = NetworkFakeDataGenerator.get_nodetype('Provider')
        providers = NodeHandle.objects.filter(node_type=provider_type)

        max_providers = self.max_cable_providers
        provider = None

        if not providers or len(providers) < max_providers:
            provider = self.create_provider()
        else:
            provider = random.choice(list(providers))

        # add data
        framing_types = self.get_dropdown_keys('optical_path_framing')
        capaticy_types = self.get_dropdown_keys('optical_path_capacity')
        operational_states = self.get_dropdown_keys('operational_states')

        data = {
            'description': self.fake.paragraph(),
            'framing': random.choice(framing_types),
            'capacity': random.choice(capaticy_types),
            'operational_state': random.choice(operational_states),
            'relationship_provider' : provider.handle_id,
        }

        for key, value in data.items():
            value = self.escape_quotes(value)
            optical_path.get_node().add_property(key, value)

        helpers.set_provider(self.user,
            optical_path.get_node(), provider.handle_id)

        # add random dependencies
        num_ports = random.randint(0, 3)

        for i in range(0, num_ports):
            dep_type = random.choice(list(self.optical_path_dependency_types.keys()))
            dep_f = self.optical_path_dependency_types[dep_type]
            dependency = dep_f()
            rel_maker = PhysicalLogicalDataRelationMaker()
            rel_maker.add_dependency(self.user, optical_path, dependency)

        return optical_path


    def create_site(self, name=None):
        # create object
        if not name:
            name = self.company_name()

        site = self.get_or_create_node(
            name, 'Site', META_TYPES[3]) # Location

        # add context
        self.add_network_context(site)

        # choices
        country_codes = self.get_dropdown_keys('countries')
        countries = [ x[1] for x in DropModel.get('countries').as_choices()[1:] ]
        site_types = self.get_dropdown_keys('site_types')

        data = {
            'country_code': random.choice(country_codes),
            'country': random.choice(countries),
            'longitude': self.fake.longitude(),
            'latitude': self.fake.latitude(),
            'area': self.random_county(),
            'owner_id': self.fake.license_plate(),
            'owner_site_name': self.fake.company(),
            'url': self.fake.url(),
            'telenor_subscription_id': self.fake.license_plate(),
        }

        # add site type
        if site_types:
            data['site_type'] = random.choice(site_types)

        for key, value in data.items():
            if value:
                value = self.escape_quotes(value)
                site.get_node().add_property(key, value)

        # add address
        num_address = random.randint(1, 3)

        for i in range(num_address):
            address = self.create_address(context_f=self.add_network_context)
            helpers.set_has_address(self.user, site.get_node(), address.handle_id)

        # add site owner
        site_owner = self.create_site_owner()
        helpers.set_responsible_for(self.user, site.get_node(), site_owner.handle_id)

        return site


    def create_room(self, name=None, add_parent=True):
        # create object
        if not name:
            name = '{}{}'.format(random.randint(1,20), \
                                    random.choice(string.ascii_letters).upper())

        room = self.get_or_create_node(
            name, 'Room', META_TYPES[3]) # Location

        # add context
        self.add_network_context(room)

        data = {
            'floor': str(random.randint(0, 20)),
        }

        for key, value in data.items():
            if value:
                value = self.escape_quotes(value)
                room.get_node().add_property(key, value)

        # add parent site
        if add_parent:
            parent_site = self.create_site()
            rel_maker = LocationDataRelationMaker()
            rel_maker.add_parent(self.user, room, parent_site)

        return room

    def create_rack(self, name=None, add_parent=True):
        # create object
        if not name:
            name = self.escape_quotes(self.fake.license_plate())

        rack = self.get_or_create_node(
            name, 'Rack', META_TYPES[3]) # Location

        # add context
        self.add_network_context(rack)

        data = {
            'height': str(random.randint(0, 20)),
            'depth': str(random.randint(0, 20)),
            'width': str(random.randint(0, 20)),
            'rack_units': str(random.randint(0, 20)),
        }

        for key, value in data.items():
            if value:
                value = self.escape_quotes(value)
                rack.get_node().add_property(key, value)

        # add parent room
        if add_parent:
            parent_room = self.create_room()
            rel_maker = LocationDataRelationMaker()
            rel_maker.add_parent(self.user, rack, parent_room)

        return rack

    def create_service(self, name=None):
        # import services class / types if necesary
        if not ServiceType.objects.all():
            dirpath = os.path.dirname(os.path.realpath(__file__))
            csv_file = \
                '{}/../../../../../scripts/service_types/ndn_service_types.csv'\
                    .format(dirpath)

            call_command(
                'import_service_types',
                csv_file=csv_file
            )

        default_test_gen_name = "service_id_generator"

        service_types = ServiceType.objects.all()
        service_type = random.choice(service_types)

        # get or create a default UniqueIdGenerator
        if not name:
            global_preferences = global_preferences_registry.manager()
            id_generator_name = global_preferences\
                                [NewServiceForm.Meta.id_generator_property]

            if not id_generator_name:
                global_preferences[NewServiceForm.Meta.id_generator_property] =\
                        default_test_gen_name

            id_generator = UniqueIdGenerator.objects.get_or_create(
                name=default_test_gen_name,
                zfill=False,
                creator=self.user,
                modifier=self.user,
            )[0]

            # id_collection is always the same so we do not need config
            name = unique_ids.get_collection_unique_id(
                                    id_generator, NordunetUniqueId)

        # create object
        service = self.get_or_create_node(
            name, 'Service', META_TYPES[1]) # Logical

        # add context
        self.add_network_context(service)

        # check if there's any provider or if we should create one
        provider_type = NetworkFakeDataGenerator.get_nodetype('Provider')
        providers = NodeHandle.objects.filter(node_type=provider_type)

        max_providers = self.max_cable_providers
        provider = None

        operational_states = self.get_dropdown_keys('operational_states')

        if not providers or len(providers) < max_providers:
            provider = self.create_provider()
        else:
            provider = random.choice(list(providers))

        helpers.set_provider(self.user, service.get_node(), provider.handle_id)

        service_type_name = service_type.name
        operational_state = random.choice(operational_states)

        data = {
            'service_class': service_type.service_class.name,
            'service_type': service_type_name,
            'operational_state': random.choice(operational_states),
            'description': self.fake.paragraph(),
            'relationship_provider' : provider.handle_id,
        }

        if service_type_name == "Project":
            data['project_end_date'] = self.fake.date_time_this_year()\
                                        .isoformat().split('T')[0]

        if data['operational_state'] == "Decommissioned":
            data['decommissioned_date'] = self.fake.date_time_this_year()\
                                            .isoformat().split('T')[0]

        for key, value in data.items():
            if value:
                value = self.escape_quotes(value)
                service.get_node().add_property(key, value)

        # set responsible and support groups
        group_type = NetworkFakeDataGenerator.get_nodetype('Group')
        groups_nhs = NodeHandle.objects.filter(node_type=group_type)

        responsible_group = None
        support_group = None
        community_generator = CommunityFakeDataGenerator()

        if groups_nhs.exists():
            responsible_group = random.choice(groups_nhs)
            support_group = random.choice(groups_nhs)
        else:
            responsible_group = community_generator.create_group()
            support_group = community_generator.create_group()

        helpers.set_takes_responsibility(
            self.user, service.get_node(), responsible_group.handle_id)
        helpers.set_supports(
            self.user, service.get_node(), support_group.handle_id)

        # add users
        num_users = random.randint(0, 4)

        for i in range(0, num_users):
            user_type = random.choice(list(self.service_user_categories.keys()))
            user_f = self.service_user_categories[user_type]
            user = user_f()
            rel_maker = LogicalDataRelationMaker()
            rel_maker.add_user(self.user, service, user)

        # add dependencies
        num_dependencies = random.randint(0, 4)

        for i in range(0, num_dependencies):
            dep_type = random.choice(list(self.service_dependency_types.keys()))
            dep_f = self.service_dependency_types[dep_type]
            dependency = dep_f()
            rel_maker = PhysicalLogicalDataRelationMaker()
            rel_maker.add_dependency(self.user, service, dependency)

        return service


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

    def add_user(self, user, main_logical_nh, usr_relation_nh):
        helpers.set_user(user, main_logical_nh.get_node(),
                            usr_relation_nh.handle_id)


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

    def add_has(self, user, physical_nh, physical_has_nh):
        helpers.set_has(user, physical_nh.get_node(),
                                    physical_has_nh.handle_id)


class LocationDataRelationMaker(DataRelationMaker):
    def add_parent(self, user, location_nh, parent_nh):
        helpers.set_has(user, parent_nh.get_node(), location_nh.handle_id)
