# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django import forms
from . import common


class NewSunetSiteForm(common.NewSiteForm):
    """
    Concatenate country code with site name
    """
    name = forms.CharField()
    country_code = forms.CharField(widget=forms.widgets.HiddenInput, initial='SE')
    address = forms.CharField(required=False)
    postarea = forms.CharField(required=False)
    postcode = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super(NewSunetSiteForm, self).clean()
        cleaned_data['country'] = common.COUNTRY_MAP[cleaned_data['country_code']]
        return cleaned_data
