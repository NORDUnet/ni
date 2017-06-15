# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django import forms
from django.db import IntegrityError
from apps.noclook.models import UniqueIdGenerator, NordunetUniqueId, NodeHandle
from apps.noclook.helpers import get_provider_id
from .. import unique_ids
from . import common


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
                    if NodeHandle.objects.filter(node_name=name):
                        self.add_error('name', e.message)
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


class NewServiceForm(common.NewServiceForm):
    def __init__(self, *args, **kwargs):
        super(NewServiceForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].initial = get_provider_id('NORDUnet')

    project_end_date = common.DatePickerField(required=False)

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


class NewOpticalLinkForm(common.NewOpticalLinkForm):
    def __init__(self, *args, **kwargs):
        super(NewOpticalLinkForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].initial = get_provider_id('NORDUnet')

    class Meta(common.NewOpticalLinkForm.Meta):
        id_generator_name = 'nordunet_optical_link_id'
        id_collection = NordunetUniqueId

    name = forms.CharField(required=False, widget=forms.widgets.HiddenInput)

    def clean(self):
        cleaned_data = super(NewOpticalLinkForm, self).clean()
        return cleaned_data


class EditOpticalLinkForm(common.EditOpticalLinkForm):
    name = forms.CharField(required=False, widget=forms.widgets.HiddenInput)


class NewOpticalMultiplexSectionForm(common.NewOpticalMultiplexSectionForm):
    def __init__(self, *args, **kwargs):
        super(NewOpticalMultiplexSectionForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].initial = get_provider_id('NORDUnet')


class NewOpticalPathForm(common.NewOpticalPathForm):

    class Meta(common.NewOpticalLinkForm.Meta):
        id_generator_name = 'nordunet_optical_path_id'
        id_collection = NordunetUniqueId

    name = forms.CharField(required=False, widget=forms.widgets.HiddenInput)

    def clean(self):
        cleaned_data = super(NewOpticalPathForm, self).clean()
        return cleaned_data


class EditOpticalPathForm(common.EditOpticalPathForm):
    name = forms.CharField(required=False, widget=forms.widgets.HiddenInput)


class NewSiteForm(common.NewSiteForm):
    """
    Concatenate country code with site name
    """

    def clean(self):
        cleaned_data = super(NewSiteForm, self).clean()
        cleaned_data['name'] = '%s-%s' % (cleaned_data['country_code'], cleaned_data['name'].upper())
        return cleaned_data
