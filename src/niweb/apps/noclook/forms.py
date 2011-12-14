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
    street = forms.CharField(required=False)
    post_area = forms.CharField(required=False)
    post_code = forms.CharField(required=False)
    country_code = forms.ChoiceField(choices=COUNTRIES, widget=forms.widgets.Select)
