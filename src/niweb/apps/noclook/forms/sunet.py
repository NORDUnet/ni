# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django import forms
from . import common


SITE_TYPES = [
    ('', ''),
    ('ILA', 'ILA'),
    ('Roadm', 'Roadm'),
    ('Stam', 'Stam'),
    ('Customer', 'Customer'),
]

RESPONSIBLE_GROUPS = [
    ('', ''),
    ('DEV', 'DEV'),
    ('NOC', 'NOC'),
    ('NPE', 'NPE'),
    ('SWAMID', 'SWAMID'),
]


class EditHostForm(common.EditHostForm):

    def __init__(self, *args, **kwargs):
        super(EditHostForm, self).__init__(*args, **kwargs)
        self.fields['responsible_group'].choices = RESPONSIBLE_GROUPS
        self.fields['support_group'].choices = RESPONSIBLE_GROUPS


class EditServiceForm(common.EditServiceForm):
    def __init__(self, *args, **kwargs):
        super(EditServiceForm, self).__init__(*args, **kwargs)
        self.fields['responsible_group'].choices = RESPONSIBLE_GROUPS
        self.fields['support_group'].choices = RESPONSIBLE_GROUPS


class NewSiteForm(common.NewSiteForm):

    name = forms.CharField()
    country_code = forms.CharField(widget=forms.widgets.HiddenInput, initial='SE')

    def clean(self):
        cleaned_data = super(NewSiteForm, self).clean()
        cleaned_data['country'] = common.COUNTRY_MAP[cleaned_data['country_code']]
        return cleaned_data


class EditSiteForm(common.EditSiteForm):

    def __init__(self, *args, **kwargs):
        super(EditSiteForm, self).__init__(*args, **kwargs)
        self.fields['site_type'].choices = SITE_TYPES
