from django import forms

COUNTRIES = [('SE', 'Sweden'), ('DK', 'Denmark')]

class SiteForm(forms.Form):
    name = forms.CharField()
    country = forms.ChoiceField(choices = COUNTRIES, widget = forms.widgets.RadioSelect())
