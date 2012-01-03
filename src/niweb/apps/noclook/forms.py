from django import forms
import norduni_client as nc

COUNTRY_CODES = [
    ('DE', 'DE'),    
    ('DK', 'DK'),
    ('FI', 'FI'),
    ('IS', 'IS'),
    ('NL', 'NL'),
    ('NO', 'NO'),
    ('SE', 'SE'),    
    ('UK', 'UK'),
    ('US', 'US')
]

COUNTRIES = [
    ('',''),
    ('Denmark', 'Denmark'),
    ('Germany', 'Germany'),
    ('Finland', 'Finland'),
    ('Iceland', 'Iceland'),
    ('Netherlands', 'Netherlands'),
    ('Norway', 'Norway'),
    ('Sweden', 'Sweden'),
    ('United Kingdom', 'United Kingdom'),
    ('USA', 'USA'),
]

SITE_TYPES = [
    ('',''),
    ('POP', 'POP'),
    ('Regenerator', 'Regenerator'),
    ('Optical Amplifier', 'Optical Amplifier')
]

CABLE_TYPES = [
    ('',''),
    ('Fiber', 'Fiber'),
    ('TP', 'TP')
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
    country = forms.ChoiceField(choices=COUNTRIES, widget=forms.widgets.Select,
                                required=False)
    site_type = forms.ChoiceField(choices=SITE_TYPES,
                                  widget=forms.widgets.Select, required=False)
    address = forms.CharField(required=False)
    postarea = forms.CharField(required=False)
    postcode = forms.CharField(required=False)
    area = forms.CharField(required=False,
                           help_text='State, county or similar.')
    longitude = forms.DecimalField(required=False, help_text='Decimal Degrees')
    latitude = forms.DecimalField(required=False, help_text='Decimal Degrees')
    telenor_subscription_id = forms.CharField(required=False)
    owner_id = forms.CharField(required=False)
    # Get Site Owner nodes
    index = nc.get_node_index(nc.neo4jdb, 'node_types')
    site_owner_nodes = nc.iter2list(index['node_type']['Site Owner'])
    site_owners = [('','')]
    for owner_node in site_owner_nodes:
        site_owners.append((owner_node.id, owner_node['name']))
    relationship_site_owners = forms.ChoiceField(choices = site_owners,
                                    widget=forms.widgets.Select, required=False)
                              
                              
class NewSiteOwnerForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')


class EditSiteOwnerForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')


class NewCableForm(forms.Form):
    name = forms.CharField()
    cable_type = forms.ChoiceField(choices=CABLE_TYPES,
                                   widget=forms.widgets.Select)
                                   
                                       
class EditCableForm(forms.Form):
    name = forms.CharField()
    cable_type = forms.ChoiceField(choices=CABLE_TYPES,
                                   widget=forms.widgets.Select)
    telenor_tn1_number = forms.CharField(required=False,
                                  help_text='Telenor TN1 number, nnn-nnnn.')
    telenor_trunk_id = forms.CharField(required=False, 
                                       help_text='Telenor Trunk ID, nnnnn.')