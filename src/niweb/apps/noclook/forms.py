from django import forms

COUNTRIES = [
    ('SE', 'Sweden'),
    ('DK', 'Denmark'),
    ('FI', 'Finland'),
    ('NO', 'Norway'),
    ('DE', 'Germany'),
    ('IS', 'Iceland'),
    ('UK', 'Great Britain'),
    ('US', 'United States'),
    ('NL', 'Netherlands')
]

class SiteForm(forms.Form):
    name = forms.CharField()
    country_code = forms.ChoiceField(choices=COUNTRIES, widget=forms.widgets.RadioSelect)
