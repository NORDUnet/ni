# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django import forms
from django.forms.utils import ErrorDict, ErrorList
from django.db import IntegrityError
from apps.noclook.models import UniqueIdGenerator, NordunetUniqueId
from apps.noclook.helpers import get_provider_id
from .. import unique_ids
from . import common


SITE_TYPES = [
    ('', ''),
    ('POP', 'POP'),
    ('Regenerator', 'Regenerator'),
    ('Optical Amplifier', 'Optical Amplifier'),
    ('Passive ODF', 'Passive ODF')
]

SERVICE_TYPES = [
    ('', ''),
    ('Alien wavelenght', 'DWDM - Alien wavelenght'),
    ('Ethernet', 'DWDM - Ethernet'),
    ('SDH', 'DWDM - SDH'),
    ('Interface Switch', 'Ethernet - Interface Switch'),
    ('External', 'External Service'),
    ('Hosting', 'Hosting'),
    ('CFG Management', 'Internal - CFG Management'),
    ('Mail', 'Internal - Mail'),
    ('NDN CoreInfra', 'Internal - NDN CoreInfra'),
    ('NDN IDM', 'Internal - NDN IDM'),
    ('NDN Instrumentation', 'Internal - NDN Instrumentation'),
    ('NDN Tools', 'Internal - NDN Tools'),
    ('NDN Tor', 'Internal - NDN Tor'),
    ('CMS', 'IAAS - CMS'),
    ('EDUID', 'IAAS - EDUID'),
    ('HSM', 'IAAS - HSM'),
    ('Social2SAML', 'IAAS - Social2SAML'),
    ('Storage', 'IAAS - Storage'),
    ('TCS', 'IAAS - TCS'),
    ('VConf', 'IAAS - VConf'),
    ('VMWare', 'IAAS - VMWare'),
    ('Backbone', 'IP - Backbone'),
    ('Customer Connection', 'IP - Customer Connection'),
    ('Internet Exchange', 'IP - Internet Exchange'),
    ('Private Interconnect', 'IP - Private Interconnect'),
    ('Private Interconnection', 'IP - Private Interconnection'),
    ('Project', 'IP - Project'),
    ('Transit', 'IP - Transit'),
    ('L2VPN', 'MPLS - L2VPN'),
    ('L3VPN', 'MPLS - L3VPN'),
    ('VPLS', 'MPLS - VPLS'),
    ('CanIt', 'SAAS - CanIt'),
    ('Connect', 'SAAS - Connect'),
    ('Kaltura', 'SAAS - Kaltura'),
    ('Survey', 'SAAS - Survey'),
    ('Box', 'SAAS - Box'),
]

SERVICE_CLASS_MAP = {
    'Alien wavelenght': 'DWDM',
    'Backbone': 'IP',
    'Box': 'SAAS',
    'CanIt': 'SAAS',
    'CFG Management': 'Internal',
    'CMS': 'IAAS',
    'Connect': 'SAAS',
    'Customer Connection': 'IP',
    'EDUID': 'IAAS',
    'HSM': 'IAAS',
    'Ethernet': 'DWDM',
    'External': 'External',
    'Hosting': 'Hosting',
    'Interface Switch': 'Ethernet',
    'Internal': 'Internal',
    'Internet Exchange': 'IP',
    'Kaltura': 'SAAS',
    'L2VPN': 'MPLS',
    'L3VPN': 'MPLS',
    'Mail': 'Internal',
    'NDN CoreInfra': 'Internal',
    'NDN IDM': 'Internal',
    'NDN Instrumentation': 'Internal',
    'NDN Tor': 'Internal',
    'NDN Tools': 'Internal',
    'Private Interconnect': 'IP',
    'Private Interconnection': 'IP',
    'Project': 'IP',
    'SDH': 'DWDM',
    'Social2SAML': 'IAAS',
    'Storage': 'IAAS',
    'Survey': 'SAAS',
    'TCS': 'IAAS',
    'Transit': 'IP',
    'VConf': 'IAAS',
    'VPLS': 'MPLS',
    'VMWare': 'IAAS',
}

OPTICAL_LINK_TYPES = [
    ('', ''),
    ('OTS', 'OTS'),
    ('OPS', 'OPS'),
]

OPTICAL_PATH_FRAMING = [
    ('', ''),
    ('OTN(CBR)', 'OTN(CBR)'),
    ('OTN(Ethernet)', 'OTN(Ethernet)'),
    ('WDM', 'WDM'),
    ('WDM(Ethernet)', 'WDM(Ethernet)'),
    ('WDM(CBR)', 'WDM(CBR)'),
    ('WDM(OTN)', 'WDM(OTN)'),
]

OPTICAL_PATH_CAPACITY = [
    ('', ''),
    ('10Gb', '10Gb'),
    ('100Gb', '100Gb'),
    ('CBR', 'CBR'),
    ('cbr 10Gb', 'cbr 10Gb'),
]

OPTICAL_LINK_INTERFACE_TYPE = [
    ('', ''),
    ('WDM', 'WDM'),
]

RESPONSIBLE_GROUPS = [
    ('', ''),
    ('ADMIN', 'ADMIN'),
    ('DEV', 'DEV'),
    ('EDUIX', 'EDUIX'),
    ('FUNET', 'FUNET'),
    ('NDGF', 'NDGF'),
    ('NOC', 'NOC'),
    ('NPE', 'NPE'),
    ('RHNET', 'RHNET'),
    ('SUNET', 'SUNET'),
    ('SWAMID', 'SWAMID'),
    ('UNINETT', 'UNINETT'),
    ('WAYF', 'WAYF'),
]


class NewCableForm(common.NewCableForm):
    def __init__(self, *args, **kwargs):
        super(NewCableForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].initial = get_provider_id('NORDUnet')

    name = forms.CharField(required=False,
                           help_text="If no name is specified the next NORDUnet cable ID will be used.")

    class Meta:
        id_generator_name = 'nordunet_cable_id'
        id_collection = NordunetUniqueId

    def clean(self):
        """
        Sets name to next generated ID or register the name in the ID collection.
        """
        cleaned_data = super(NewCableForm, self).clean()
        # Set name to a generated id if the cable is not a manually named cable.
        name = cleaned_data.get("name")
        if self.is_valid():
            if not name:
                if not self.Meta.id_generator_name or not self.Meta.id_collection:
                    raise Exception('You have to set id_generator_name and id_collection in form Meta class.')
                try:
                    id_generator = UniqueIdGenerator.objects.get(name=self.Meta.id_generator_name)
                    cleaned_data['name'] = unique_ids.get_collection_unique_id(id_generator, self.Meta.id_collection)
                except UniqueIdGenerator.DoesNotExist as e:
                    raise e
            else:
                try:
                    unique_ids.register_unique_id(self.Meta.id_collection, name)
                except IntegrityError as e:
                    self._errors = ErrorDict()
                    self._errors['name'] = ErrorList()
                    self._errors['name'].append(e.message)
        return cleaned_data


class NewServiceForm(common.NewServiceForm):
    def __init__(self, *args, **kwargs):
        super(NewServiceForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].initial = get_provider_id('NORDUnet')

    project_end_date = forms.DateField(required=False)

    class Meta(common.NewServiceForm.Meta):
        id_generator_name = 'nordunet_service_id'
        id_collection = NordunetUniqueId

    def clean(self):
        """
        Checks that project_end_date was not omitted if service is of type project.
        """
        cleaned_data = super(NewServiceForm, self).clean()
        if cleaned_data['service_type'] == 'Project' and not cleaned_data['project_end_date']:
            self._errors = ErrorDict()
            self._errors['project_end_date'] = ErrorList()
            self._errors['project_end_date'].append('Missing project end date.')
        # Convert  project_end_date to string if set
        if cleaned_data.get('project_end_date', None):
            cleaned_data['project_end_date'] = cleaned_data['project_end_date'].strftime('%Y-%m-%d')
        return cleaned_data


class NewL2vpnServiceForm(NewServiceForm):

    ncs_service_name = forms.CharField(required=False, help_text='')
    vpn_type = forms.CharField(required=False, help_text='')
    vlan = forms.CharField(required=False, help_text='')
    vrf_target = forms.CharField(required=False, help_text='')
    route_distinguisher = forms.CharField(required=False, help_text='')


class NewOpticalLinkForm(common.NewOpticalLinkForm):
    def __init__(self, *args, **kwargs):
        super(NewOpticalLinkForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].initial = get_provider_id('NORDUnet')
        self.fields['interface_type'].initial = 'WDM'

    class Meta(common.NewOpticalLinkForm.Meta):
        id_generator_name = 'nordunet_optical_link_id'
        id_collection = NordunetUniqueId

    def clean(self):
        cleaned_data = super(NewOpticalLinkForm, self).clean()
        return cleaned_data


class NewOpticalPathForm(common.NewOpticalPathForm):
    def __init__(self, *args, **kwargs):
        super(NewOpticalPathForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].initial = get_provider_id('NORDUnet')

    class Meta(common.NewOpticalLinkForm.Meta):
        id_generator_name = 'nordunet_optical_path_id'
        id_collection = NordunetUniqueId

    def clean(self):
        cleaned_data = super(NewOpticalPathForm, self).clean()
        return cleaned_data


class NewSiteForm(common.NewSiteForm):
    """
    Concatenate country code with site name
    """

    def clean(self):
        cleaned_data = super(NewSiteForm, self).clean()
        cleaned_data['name'] = '%s-%s' % (cleaned_data['country_code'], cleaned_data['name'].upper())
        return cleaned_data
