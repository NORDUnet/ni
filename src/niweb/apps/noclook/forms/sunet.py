# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django import forms
from . import common


SITE_TYPES = [
    ('', ''),
    ('ILA', 'ILA'),
    ('Roadm', 'Roadm'),
    ('Stam', 'Stam'),
]

RESPONSIBLE_GROUPS = [
    ('', ''),
    ('DEV', 'DEV'),
    ('NOC', 'NOC'),
    ('NPE', 'NPE'),
    ('SWAMID', 'SWAMID'),
]


class NewSiteForm(common.NewSiteForm):
    """
    Concatenate country code with site name
    """
    name = forms.CharField()
    country_code = forms.CharField(widget=forms.widgets.HiddenInput, initial='SE')

    def clean(self):
        cleaned_data = super(NewSiteForm, self).clean()
        cleaned_data['country'] = common.COUNTRY_MAP[cleaned_data['country_code']]
        return cleaned_data
