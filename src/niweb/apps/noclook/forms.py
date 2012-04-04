from django import forms
from niweb.apps.noclook import helpers as h
import norduni_client as nc

# We should move this kind of data to the SQL database.
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
    ('Optical Amplifier', 'Optical Amplifier'),
    ('Passive ODF', 'Passive ODF')
]

CABLE_TYPES = [
    ('',''),
    ('Fiber', 'Fiber'),
    ('TP', 'TP')
]

def get_node_type_tuples(node_type):
    '''
    Returns a list of tuples of node.id and node['name'] of the node_type.
    '''
    from operator import itemgetter
    index = nc.get_node_index(nc.neo4jdb, 'node_types')
    nodes = h.iter2list(index['node_type'][node_type])
    node_list = [('','')]
    for node in nodes:
        if node_type == 'Site':
            site_name = '%s-%s' % (node.getProperty('country_code', ''), 
                                   node['name'])
            node_list.append((node.id, site_name))
        else:
            node_list.append((node.id, node['name']))
    node_list.sort(key=itemgetter(1))
    return node_list


class NewSiteForm(forms.Form):
    name = forms.CharField()
    country_code = forms.ChoiceField(choices=COUNTRY_CODES,
                                     widget=forms.widgets.Select)
    address = forms.CharField(required=False)
    postarea = forms.CharField(required=False)
    postcode = forms.CharField(required=False)
    
    
class EditSiteForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(EditSiteForm, self).__init__(*args, **kwargs)
        self.fields['relationship_site_owners'].choices = get_node_type_tuples('Site Owner')
    
    name = forms.CharField()
    country_code = forms.ChoiceField(choices=COUNTRY_CODES,
                                     widget=forms.widgets.Select)
    country = forms.ChoiceField(choices=COUNTRIES, widget=forms.widgets.Select,
                                required=False)
    site_type = forms.ChoiceField(choices=SITE_TYPES,
                                  widget=forms.widgets.Select, required=False)
    address = forms.CharField(required=False)
    floor = forms.CharField(required=False,
                            help_text='Floor of building if applicable.')
    room = forms.CharField(required=False,
                         help_text='Room identifier in building if applicable.')
    postarea = forms.CharField(required=False)
    postcode = forms.CharField(required=False)
    area = forms.CharField(required=False,
                           help_text='State, county or similar.')
    longitude = forms.FloatField(required=False, help_text='Decimal Degrees')
    latitude = forms.FloatField(required=False, help_text='Decimal Degrees')
    telenor_subscription_id = forms.CharField(required=False)
    owner_id = forms.CharField(required=False)
    owner_site_name = forms.CharField(required=False)
    relationship_site_owners = forms.ChoiceField(widget=forms.widgets.Select,
                                                 required=False)
                              
                              
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
                                  help_text='Telenor TN1 number, nnnnn.')
    telenor_trunk_id = forms.CharField(required=False, 
                                       help_text='Telenor Trunk ID, nnn-nnnn.')
    global_crossing_circuit_id = forms.CharField(required=False,
                                                 help_text='Global Crossing \
                                                 circuit ID, nnnnnnnnnn')
    relationship_end_a = forms.IntegerField(required=False,
                                            widget=forms.widgets.HiddenInput)
    relationship_end_b = forms.IntegerField(required=False,
                                            widget=forms.widgets.HiddenInput)


class EditOpticalNodeForm(forms.Form):        
    name = forms.CharField()
    sites = get_node_type_tuples('Site')
    relationship_location = forms.IntegerField(required=False,
                                            widget=forms.widgets.HiddenInput)
                                              

class EditPeeringPartnerForm(forms.Form):
    name = forms.CharField()


class NewRackForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(NewRackForm, self).__init__(*args, **kwargs)
        self.fields['relationship_location'].choices = get_node_type_tuples('Site')
    
    name = forms.CharField(help_text='Name should be the grid location.')
    relationship_location = forms.ChoiceField(required=False,
                                              widget=forms.widgets.Select)
                                              
                                        
class EditRackForm(forms.Form):
    name = forms.CharField(help_text='Name should be the site grid location.')
    height = forms.IntegerField(required=False, 
                                help_text='Height in millimeters (mm).')
    depth = forms.IntegerField(required=False,
                               help_text='Depth in millimeters (mm).')
    width = forms.IntegerField(required=False,
                               help_text='Width in millimeters (mm).')
    relationship_location = forms.IntegerField(required=False,
                                            widget=forms.widgets.HiddenInput)
                
                
class EditHostForm(forms.Form):
    #units = forms.IntegerField(required=False,
    #                           help_text='Height in rack units (u).')
    #start_unit = forms.IntegerField(required=False,
    #                           help_text='Where the host starts in the rack. \
    #                           Used for calculation of rack space.')
    relationship_location = forms.IntegerField(required=False,
                                            widget=forms.widgets.HiddenInput)


class EditRouterForm(forms.Form):
    #units = forms.IntegerField(required=False,
    #                           help_text='Height in rack units (u).')
    #start_unit = forms.IntegerField(required=False,
    #                           help_text='Where the host starts in the rack. \
    #                           Used for calculation of rack space.')
    relationship_location = forms.IntegerField(required=False,
                                            widget=forms.widgets.HiddenInput)
    
    
class NewOdfForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(NewOdfForm, self).__init__(*args, **kwargs)
        # Set max number of ports to choose from
        num_of_ports = 20
        choices = [(x,x) for x in range(1, num_of_ports+1) if x]
        self.fields['number_of_ports'].choices = choices
        
    #units = forms.IntegerField(required=False,
    #                           help_text='Height in rack units (u).')
    #start_unit = forms.IntegerField(required=False,
    #                           help_text='Where the host starts in the rack. \
    #                           Used for calculation of rack space.')
    name = forms.CharField()
    number_of_ports = forms.ChoiceField(required=False,
                                              widget=forms.widgets.Select)


class EditOdfForm(forms.Form):
    #units = forms.IntegerField(required=False,
    #                           help_text='Height in rack units (u).')
    #start_unit = forms.IntegerField(required=False,
    #                           help_text='Where the host starts in the rack. \
    #                           Used for calculation of rack space.')
    name = forms.CharField()
    relationship_location = forms.IntegerField(required=False,
                                               widget=forms.widgets.HiddenInput)
                                              