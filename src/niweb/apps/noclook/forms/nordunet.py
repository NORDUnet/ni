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
    ('MEDIA', 'Media Services'),
    ('NDGF', 'NDGF'),
    ('NOC', 'NOC'),
    ('NPE', 'NPE'),
    ('RHNET', 'RHNET'),
    ('SEI', 'SEI'),
    ('SUNET', 'SUNET'),
    ('SWAMID', 'SWAMID'),
    ('UNINETT', 'UNINETT'),
    ('WAYF', 'WAYF'),
]

HOST_MANAGEMENT_SW = [
    ('', ''),
    ('CFEngine', 'CFEngine'),
    ('Manual', 'Manual'),
    ('Puppet', 'Puppet'),
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


class EditCableForm(common.EditCableForm):
    name = forms.CharField(help_text='Name will be superseded by Telenor Trunk ID if set.')
    telenor_tn1_number = forms.CharField(required=False, help_text='Telenor TN1 number, nnnnn.', label='TN1 Number')
    telenor_trunk_id = forms.CharField(required=False, help_text='Telenor Trunk ID, nnn-nnnn.', label='Trunk ID')
    global_crossing_circuit_id = forms.CharField(required=False, help_text='Global Crossing circuit ID, nnnnnnnnnn', label='Circuit ID')
    global_connect_circuit_id = forms.CharField(required=False, help_text='Global Connect circuit ID', label='Circuit ID')

    def clean(self):
        cleaned_data = super(EditCableForm, self).clean()
        if cleaned_data.get('telenor_trunk_id', None):
            cleaned_data['name'] = cleaned_data['telenor_trunk_id']
        return cleaned_data


class EditHostForm(common.EditHostForm):

    def __init__(self, *args, **kwargs):
        super(EditHostForm, self).__init__(*args, **kwargs)
        self.fields['responsible_group'].choices = RESPONSIBLE_GROUPS
        self.fields['support_group'].choices = RESPONSIBLE_GROUPS
        self.fields['managed_by'].choices = HOST_MANAGEMENT_SW


class NewServiceForm(common.NewServiceForm):
    def __init__(self, *args, **kwargs):
        super(NewServiceForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].initial = get_provider_id('NORDUnet')

    project_end_date = forms.DateField(required=False)

    def clean(self):
        """
        Checks that project_end_date was not omitted if service is of type project.
        """
        cleaned_data = super(NewServiceForm, self).clean()
        if cleaned_data['service_type'] == 'Project' and not cleaned_data['project_end_date']:
            self.add_error('project_end_date', 'Missing project end date.')
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


class EditServiceForm(common.EditServiceForm):
    def __init__(self, *args, **kwargs):
        super(EditServiceForm, self).__init__(*args, **kwargs)
        self.fields['responsible_group'].choices = RESPONSIBLE_GROUPS
        self.fields['support_group'].choices = RESPONSIBLE_GROUPS

class NewOpticalLinkForm(common.NewOpticalLinkForm):
    def __init__(self, *args, **kwargs):
        super(NewOpticalLinkForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].initial = get_provider_id('NORDUnet')
        self.fields['link_type'].choices = OPTICAL_LINK_TYPES
        self.fields['interface_type'].choices = OPTICAL_LINK_INTERFACE_TYPE
        self.fields['interface_type'].initial = 'WDM'

    class Meta(common.NewOpticalLinkForm.Meta):
        id_generator_name = 'nordunet_optical_link_id'
        id_collection = NordunetUniqueId

    name = forms.CharField(required=False, widget=forms.widgets.HiddenInput)

    def clean(self):
        cleaned_data = super(NewOpticalLinkForm, self).clean()
        return cleaned_data


class EditOpticalLinkForm(common.EditOpticalLinkForm):

    def __init__(self, *args, **kwargs):
        super(EditOpticalLinkForm, self).__init__(*args, **kwargs)
        self.fields['link_type'].choices = OPTICAL_LINK_TYPES
        self.fields['interface_type'].choices = OPTICAL_LINK_INTERFACE_TYPE

    name = forms.CharField(required=False, widget=forms.widgets.HiddenInput)


class NewOpticalMultiplexSectionForm(common.NewOpticalMultiplexSectionForm):
    def __init__(self, *args, **kwargs):
        super(NewOpticalMultiplexSectionForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].initial = get_provider_id('NORDUnet')


class NewOpticalPathForm(common.NewOpticalPathForm):
    def __init__(self, *args, **kwargs):
        super(NewOpticalPathForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].initial = get_provider_id('NORDUnet')
        self.fields['framing'].choices = OPTICAL_PATH_FRAMING
        self.fields['capacity'].choices = OPTICAL_PATH_CAPACITY

    class Meta(common.NewOpticalLinkForm.Meta):
        id_generator_name = 'nordunet_optical_path_id'
        id_collection = NordunetUniqueId

    name = forms.CharField(required=False, widget=forms.widgets.HiddenInput)

    def clean(self):
        cleaned_data = super(NewOpticalPathForm, self).clean()
        return cleaned_data


class EditOpticalPathForm(common.EditOpticalPathForm):

    def __init__(self, *args, **kwargs):
        super(EditOpticalPathForm, self).__init__(*args, **kwargs)
        self.fields['framing'].choices = OPTICAL_PATH_FRAMING
        self.fields['capacity'].choices = OPTICAL_PATH_CAPACITY

    name = forms.CharField(required=False, widget=forms.widgets.HiddenInput)


class NewSiteForm(common.NewSiteForm):
    """
    Concatenate country code with site name
    """

    def clean(self):
        cleaned_data = super(NewSiteForm, self).clean()
        cleaned_data['name'] = '%s-%s' % (cleaned_data['country_code'], cleaned_data['name'].upper())
        return cleaned_data


class EditSiteForm(common.EditSiteForm):

    def __init__(self, *args, **kwargs):
        super(EditSiteForm, self).__init__(*args, **kwargs)
        self.fields['site_type'].choices = SITE_TYPES
