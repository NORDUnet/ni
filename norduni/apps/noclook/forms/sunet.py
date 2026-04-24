# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django import forms
from . import common
from apps.noclook.models import Dropdown


class NewSiteForm(common.NewSiteForm):

    name = forms.CharField()
    country_code = forms.CharField(widget=forms.widgets.HiddenInput,
                                   initial='SE')

    def clean(self):
        cleaned_data = super(NewSiteForm, self).clean()
        cleaned_data['country'] = common.country_map(cleaned_data['country_code'])
        return cleaned_data


class EditCableForm(common.EditCableForm):
    def __init__(self, *args, **kwargs):
        super(EditCableForm, self).__init__(*args, **kwargs)
        self.fields['tele2_cable_contract'].choices = Dropdown.get('tele2_cable_contracts').as_choices()

    tele2_cable_contract = forms.ChoiceField(required=False, label='Cable Contract')
    tele2_alternative_circuit_id = forms.CharField(required=False, help_text='Tele2 alternativ circuit ID',
                                                label='Circuit ID')
