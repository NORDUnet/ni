from django import forms

COUNTRIES = [
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

class SiteForm(forms.Form):
    name = forms.CharField()
    address = forms.CharField(required=False)
    postarea = forms.CharField(required=False)
    postcode = forms.CharField(required=False)
    country_code = forms.ChoiceField(choices=COUNTRIES, widget=forms.widgets.Select)
