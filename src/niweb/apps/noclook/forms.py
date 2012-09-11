from django import forms

from django.forms.util import ErrorDict, ErrorList
from niweb.apps.noclook.models import UniqueId
import niweb.apps.noclook.helpers as h
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

COUNTRY_MAP = {
    'DE': 'Germany',
    'DK': 'Denmark',
    'FI': 'Finland',
    'IS': 'Iceland',
    'NL': 'Netherlands',
    'NO': 'Norway',
    'SE': 'Sweden',
    'UK': 'United Kingdom',
    'US': 'USA'
}

SITE_TYPES = [
    ('',''),
    ('POP', 'POP'),
    ('Regenerator', 'Regenerator'),
    ('Optical Amplifier', 'Optical Amplifier'),
    ('Passive ODF', 'Passive ODF')
]

CABLE_TYPES = [
    ('',''),
    ('Dark Fiber', 'Dark Fiber'),
    ('Patch', 'Patch'),
    ('Power Cable', 'Power Cable')
]

PORT_TYPES = [
    ('',''),
    ('LC', 'LC'),
    ('MU', 'MU'),
    ('RJ45', 'RJ45'),
    ('SC', 'SC'),
]

SERVICE_TYPES = [
    ('',''),
    ('Alien wavelenght', 'Alien wavelenght'),
    ('Backbone', 'Backbone'),
    ('Customer Connection', 'Customer Connection'),
    ('Ethernet', 'Ethernet'),
    ('External', 'External'),
    ('Internet Exchange', 'Internet Exchange'),
    ('l2vpn', 'l2vpn'),
    ('l3vpn', 'l3vpn'),
    ('Private Interconnect', 'Private Interconnect'),
    ('SDH', 'SDH'),
    ('Transit', 'Transit'),
    ('vpls', 'vpls'),
]

SERVICE_CLASS_MAPS = {
    'Alien wavelenght': 'DWDM',
    'Backbone': 'IP',
    'Customer Connection': 'IP',
    'Ethernet': 'DWDM',
    'Internet Exchange': 'IP',
    'l2vpn': 'MPLS',
    'l3vpn': 'MPLS',
    'Private Interconnect': 'IP',
    'SDH': 'DWDM',
    'Transit': 'IP',
    'vpls': 'MPLS',
}

def get_node_type_tuples(node_type):
    """
    Returns a list of tuple of node.id and node['name'] of the node_type.
    """
    from operator import itemgetter
    index = nc.get_node_index(nc.neo4jdb, 'node_types')
    nodes = h.iter2list(index['node_type'][node_type])
    node_list = [('','')]
    for node in nodes:
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
    name = forms.CharField()
    country_code = forms.ChoiceField(choices=COUNTRY_CODES, widget=forms.widgets.Select,
                                     required=False)
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
    relationship_site_owner = forms.IntegerField(required=False,
                                            widget=forms.widgets.HiddenInput)
                              
                              
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
    def __init__(self, *args, **kwargs):
        super(EditHostForm, self).__init__(*args, **kwargs)
        self.fields['relationship_user'].choices = get_node_type_tuples('Host User')
        self.fields['relationship_owner'].choices = get_node_type_tuples('Host User')
    #units = forms.IntegerField(required=False,
    #                           help_text='Height in rack units (u).')
    #start_unit = forms.IntegerField(required=False,
    #                           help_text='Where the host starts in the rack. \
    #                           Used for calculation of rack space.')
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of what the machine is used for.')
    backup = forms.NullBooleanField(required=False, help_text='Is the host backed up?')
    syslog = forms.NullBooleanField(required=False, help_text='Do the host log to the syslog machine?')
    in_operation = forms.NullBooleanField(required=False, help_text='Backup and syslog has to be "yes" for a host to be set in operation.')
    responsible_person = forms.CharField(required=False, help_text='Name of the person responsible for the host.')
    os = forms.CharField(required=False, help_text='What operating system is running on the host?')
    os_version = forms.CharField(required=False, help_text='Which version of the operating system is running on the host?')
    model = forms.CharField(required=False, help_text='What is the hosts hardware model name?')
    vendor = forms.CharField(required=False, help_text='Name of the vendor that should be contacted for hardware support?')
    service_tag = forms.CharField(required=False, help_text='What is the vendors service tag for the host?')
    end_support = forms.DateField(required=False, help_text='When does the hardware support end?')
    relationship_location = forms.IntegerField(required=False,
                                            widget=forms.widgets.HiddenInput)
    relationship_user = forms.ChoiceField(required=False,
                                          widget=forms.widgets.Select)
    relationship_owner = forms.ChoiceField(required=False,
                                          widget=forms.widgets.Select)

    def clean(self):
        cleaned_data = super(EditHostForm, self).clean()
        backup = cleaned_data.get('backup')
        syslog = cleaned_data.get('syslog')
        in_operation = cleaned_data.get('in_operation')
        if in_operation and not (backup and syslog):
            msg = u'You can not set a host in operation without backup or syslog.'
            self._errors["in_operation"] = self.error_class([msg])
            del cleaned_data['in_operation']
        # Always return the full collection of cleaned data.
        return cleaned_data


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
        max_num_of_ports = 40
        choices = [(x,x) for x in range(1, max_num_of_ports+1) if x]
        self.fields['max_number_of_ports'].choices = choices
        
    #units = forms.IntegerField(required=False,
    #                           help_text='Height in rack units (u).')
    #start_unit = forms.IntegerField(required=False,
    #                           help_text='Where the host starts in the rack. \
    #                           Used for calculation of rack space.')
    name = forms.CharField()
    max_number_of_ports = forms.ChoiceField(required=False,
                                              widget=forms.widgets.Select)


class EditOdfForm(forms.Form):
    #units = forms.IntegerField(required=False,
    #                           help_text='Height in rack units (u).')
    #start_unit = forms.IntegerField(required=False,
    #                           help_text='Where the host starts in the rack. \
    #                           Used for calculation of rack space.')
    name = forms.CharField()
    max_number_of_ports = forms.IntegerField(help_text='Max number of ports.')
    relationship_location = forms.IntegerField(required=False,
                                               widget=forms.widgets.HiddenInput)


class NewPortForm(forms.Form):
    name = forms.CharField()
    port_type = forms.ChoiceField(choices=PORT_TYPES,
                                   widget=forms.widgets.Select)
    relationship_parent = forms.IntegerField(required=False,
                                             widget=forms.widgets.HiddenInput)


class EditPortForm(forms.Form):
    name = forms.CharField()
    port_type = forms.ChoiceField(choices=PORT_TYPES,
                                   widget=forms.widgets.Select)
    relationship_parent = forms.IntegerField(required=False,
                                             widget=forms.widgets.HiddenInput)

class NewCustomerForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')


class EditCustomerForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')


class NewEndUserForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')


class EditEndUserForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')


class NewProviderForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')


class EditProviderForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')


class NewServiceForm(forms.Form):
    name = forms.CharField(required=False)
    service_type = forms.ChoiceField(choices=SERVICE_TYPES,
                                     widget=forms.widgets.Select)
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of the service.')

    class Meta:
        id_generator_name = None
        manually_named_services = ['External'] # service_type of manually named services

    def clean(self):
        """
        Get next service ID for internal services. Only expect a user
        inputted name for manually named services.
        """
        cleaned_data = super(NewServiceForm, self).clean()
        name = cleaned_data.get("name")
        service_type = cleaned_data.get("service_type")
        if not name and service_type not in self.Meta.manually_named_services:
            if not self.Meta.id_generator_name:
                raise Exception('You have to set id_generator_name in form Meta class.')
            try:
                id_generator = UniqueId.objects.get(name=self.Meta.id_generator_name)
                cleaned_data['name'] = id_generator.get_id()
            except UniqueId.DoesNotExist as e:
                raise e
        elif not name:
            self._errors = ErrorDict()
            self._errors['name'] = ErrorList()
            self._errors['name'].append('Missing name for %s service.' % service_type)
        return cleaned_data


class NewNordunetServiceForm(NewServiceForm):

    class Meta(NewServiceForm.Meta):
        id_generator_name = 'nordunet_service_id'


class EditServiceForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(EditServiceForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')

    service_type = forms.ChoiceField(choices=SERVICE_TYPES,
                                         widget=forms.widgets.Select)
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of the service.')
    relationship_provider = forms.ChoiceField(required=False, widget=forms.widgets.Select)