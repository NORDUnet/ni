from django import forms

COUNTRY_CODES = [
    ('SE', 'SE'),
    ('DK', 'DK'),
    ('FI', 'FI'),
    ('NO', 'NO'),
    ('DE', 'DE'),
    ('IS', 'IS'),
    ('UK', 'UK'),
    ('US', 'US'),
    ('NL', 'NL')
]

COUNTRIES = [
    ('Sweden', 'Sweden'),
    ('Denmark', 'Denmark'),
    ('Germany', 'Germany'),
    ('Finland', 'Finland'),
    ('Netherlands', 'Netherlands'),
    ('Norway', 'Norway'),
    ('Island', 'Island'),
    ('United Kingdom', 'United Kingdom'),
    ('USA', 'USA'),
]

SITE_TYPES = [
    ('Unknown', 'Unknown'),
    ('POP', 'POP'),
    ('Regenerator', 'Regenerator'),
    ('Optical Amplifier', 'Optical Amplifier')
]

class NewSiteForm(forms.Form):
    name = forms.CharField()
    country_code = forms.ChoiceField(choices=COUNTRY_CODES,
                                     widget=forms.widgets.Select)
    address = forms.CharField(required=False)
    postarea = forms.CharField(required=False)
    postcode = forms.CharField(required=False)
    
    
class EditSiteForm(forms.Form):
    name = forms.CharField()
    country_code = forms.ChoiceField(choices=COUNTRY_CODES,
                                     widget=forms.widgets.Select)
    country = forms.ChoiceField(choices=COUNTRIES,
                                     widget=forms.widgets.Select)
    site_type = forms.ChoiceField(choices=SITE_TYPES,
                                  widget=forms.widgets.RadioSelect, required=False)
    address = forms.CharField(required=False)
    postarea = forms.CharField(required=False)
    postcode = forms.CharField(required=False)
    area = forms.CharField(required=False)
    longitude = forms.DecimalField(required=False)
    latitude = forms.DecimalField(required=False)
    telenor_subscription_id = forms.CharField(required=False)
    owner_id = forms.CharField(required=False)
    
    
