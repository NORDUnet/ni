from django import forms

OPERATIONAL_STATE = [
    ("In service", "In service"),
    ("Decommissioned", "Decommissioned"),
    ("Testing", "Testing"),
    ("Reserved", "Reserved"),
]
    
class HostReportForm(forms.Form):
    operational_state = forms.ChoiceField(
            choices=OPERATIONAL_STATE,
            required=False, 
            widget=forms.CheckboxSelectMultiple)

    def query():
        q = ""
        print cleaned_data

