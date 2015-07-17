from datetime import datetime
from django import forms
from django.forms.util import ErrorDict, ErrorList, ValidationError
from django.forms.widgets import HiddenInput
from django.db import IntegrityError
import json
from .models import UniqueIdGenerator, NordunetUniqueId
from . import unique_ids
import norduniclient as nc

# We should move this kind of data to the SQL database.
COUNTRY_CODES = [
    ('BE', 'BE'),
    ('DE', 'DE'),
    ('DK', 'DK'),
    ('FI', 'FI'),
    ('FR', 'FR'),
    ('IS', 'IS'),
    ('NL', 'NL'),
    ('NO', 'NO'),
    ('SE', 'SE'),    
    ('UK', 'UK'),
    ('US', 'US')
]

COUNTRIES = [
    ('', ''),
    ('Belgium', 'Belgium'),
    ('Denmark', 'Denmark'),
    ('Germany', 'Germany'),
    ('Finland', 'Finland'),
    ('France', 'France'),
    ('Iceland', 'Iceland'),
    ('Netherlands', 'Netherlands'),
    ('Norway', 'Norway'),
    ('Sweden', 'Sweden'),
    ('United Kingdom', 'United Kingdom'),
    ('USA', 'USA'),
]

COUNTRY_MAP = {
    'BE': 'Belgium',
    'DE': 'Germany',
    'DK': 'Denmark',
    'FI': 'Finland',
    'FR': 'France',
    'IS': 'Iceland',
    'NL': 'Netherlands',
    'NO': 'Norway',
    'SE': 'Sweden',
    'UK': 'United Kingdom',
    'US': 'USA'
}

COUNTRY_CODE_MAP = dict((COUNTRY_MAP[key], key) for key in COUNTRY_MAP)

SITE_TYPES = [
    ('', ''),
    ('POP', 'POP'),
    ('Regenerator', 'Regenerator'),
    ('Optical Amplifier', 'Optical Amplifier'),
    ('Passive ODF', 'Passive ODF')
]

CABLE_TYPES = [
    ('', ''),
    ('Dark Fiber', 'Dark Fiber'),
    ('Patch', 'Patch'),
    ('Power Cable', 'Power Cable')
]

PORT_TYPES = [
    ('', ''),
    ('C13 / C14', 'C13 / C14'),
    ('C19 / C20', 'C19 / C20'),
    ('CEE', 'CEE'),
    ('E2000', 'E2000'),
    ('Fixed', 'Fixed'),
    ('LC', 'LC'),
    ('MU', 'MU'),
    ('RJ45', 'RJ45'),
    ('SC', 'SC'),
    ('Schuko', 'Schuko'),
]

SERVICE_TYPES = [
    ('', ''),
    ('Alien wavelenght', 'DWDM - Alien wavelenght'),
    ('Ethernet', 'DWDM - Ethernet'),
    ('SDH', 'DWDM - SDH'),
    ('Interface Switch', 'Ethernet - Interface Switch'),
    ('External', 'External Service'),
    ('Hosting', 'Hosting'),
    ('CFG Management', 'Internal - CFG Management'),
    ('Mail', 'Internal - Mail'),
    ('NDN CoreInfra', 'Internal - NDN CoreInfra'),
    ('NDN IDM', 'Internal - NDN IDM'),
    ('NDN Instrumentation', 'Internal - NDN Instrumentation'),
    ('NDN Tools', 'Internal - NDN Tools'),
    ('NDN Tor', 'Internal - NDN Tor'),
    ('CMS', 'IAAS - CMS'),
    ('EDUID', 'IAAS - EDUID'),
    ('HSM', 'IAAS - HSM'),
    ('Social2SAML', 'IAAS - Social2SAML'),
    ('Storage', 'IAAS - Storage'),
    ('TCS', 'IAAS - TCS'),
    ('VConf', 'IAAS - VConf'),
    ('VMWare', 'IAAS - VMWare'),
    ('Backbone', 'IP - Backbone'),
    ('Customer Connection', 'IP - Customer Connection'),
    ('Internet Exchange', 'IP - Internet Exchange'),
    ('Private Interconnect', 'IP - Private Interconnect'),
    ('Private Interconnection', 'IP - Private Interconnection'),
    ('Project', 'IP - Project'),
    ('Transit', 'IP - Transit'),
    ('L2VPN', 'MPLS - L2VPN'),
    ('L3VPN', 'MPLS - L3VPN'),
    ('VPLS', 'MPLS - VPLS'),
    ('CanIt', 'SAAS - CanIt'),
    ('Connect', 'SAAS - Connect'),
    ('Kaltura', 'SAAS - Kaltura'),
    ('Survey', 'SAAS - Survey'),
    ('Box', 'SAAS - Box'),
]

SERVICE_CLASS_MAP = {
    'Alien wavelenght': 'DWDM',
    'Backbone': 'IP',
    'Box': 'SAAS',
    'CanIt': 'SAAS',
    'CFG Management': 'Internal',
    'CMS': 'IAAS',
    'Connect': 'SAAS',
    'Customer Connection': 'IP',
    'EDUID': 'IAAS',
    'HSM': 'IAAS',
    'Ethernet': 'DWDM',
    'External': 'External',
    'Hosting': 'Hosting',
    'Interface Switch': 'Ethernet',
    'Internal': 'Internal',
    'Internet Exchange': 'IP',
    'Kaltura': 'SAAS',
    'L2VPN': 'MPLS',
    'L3VPN': 'MPLS',
    'Mail': 'Internal',
    'NDN CoreInfra': 'Internal',
    'NDN IDM': 'Internal',
    'NDN Instrumentation': 'Internal',
    'NDN Tor': 'Internal',
    'NDN Tools': 'Internal',
    'Private Interconnect': 'IP',
    'Private Interconnection': 'IP',
    'Project': 'IP',
    'SDH': 'DWDM',
    'Social2SAML': 'IAAS',
    'Storage': 'IAAS',
    'Survey': 'SAAS',
    'TCS': 'IAAS',
    'Transit': 'IP',
    'VConf': 'IAAS',
    'VPLS': 'MPLS',
    'VMWare': 'IAAS',
}

OPERATIONAL_STATES = [
    ('', ''),
    ('In service', 'In service'),
    ('Reserved', 'Reserved'),
    ('Decommissioned', 'Decommissioned'),
    ('Testing', 'Testing'),
]

OPTICAL_LINK_TYPES = [
    ('', ''),
    ('OTS', 'OTS'),
    ('OPS', 'OPS'),
]

OPTICAL_PATH_FRAMING = [
    ('', ''),
    ('OTN(CBR)', 'OTN(CBR)'),
    ('OTN(Ethernet)', 'OTN(Ethernet)'),
    ('WDM', 'WDM'),
    ('WDM(Ethernet)', 'WDM(Ethernet)'),
    ('WDM(CBR)', 'WDM(CBR)'),
    ('WDM(OTN)', 'WDM(OTN)'),
]

OPTICAL_PATH_CAPACITY = [
    ('', ''),
    ('10Gb', '10Gb'),
    ('100Gb', '100Gb'),
    ('CBR', 'CBR'),
    ('cbr 10Gb', 'cbr 10Gb'),
]

OPTICAL_LINK_INTERFACE_TYPE = [
    ('', ''),
    ('WDM', 'WDM'),
]

SECURITY_CLASSES = [
    ('', ''),
    (1, 1),
    (2, 2),
    (3, 3),
    (4, 4),
]

RESPONSIBLE_GROUPS = [
    ('', ''),
    ('ADMIN', 'ADMIN'),
    ('DEV', 'DEV'),
    ('EDUIX', 'EDUIX'),
    ('FUNET', 'FUNET'),
    ('NDGF', 'NDGF'),
    ('NOC', 'NOC'),
    ('NPE', 'NPE'),
    ('RHNET', 'RHNET'),
    ('SUNET', 'SUNET'),
    ('SWAMID', 'SWAMID'),
    ('UNINETT', 'UNINETT'),
    ('WAYF', 'WAYF'),
]


def get_node_type_tuples(node_type):
    """
    Returns a list of tuple of node.handle_id and node['name'] of label node_type.
    """
    choices = [('', '')]
    q = """
        MATCH (n:{node_type})
        RETURN n.handle_id, n.name
        ORDER BY n.name
        """.format(node_type=node_type.replace(' ', '_'))
    with nc.neo4jdb.read as r:
        choices.extend(r.execute(q).fetchall())
    return choices


class JSONField(forms.CharField):

    def __init__(self, *args, **kwargs):
        super(JSONField, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = super(JSONField, self).clean(value)
        try:
            if value:
                value = json.loads(value)
        except ValueError:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        return value


class JSONInput(HiddenInput):

    def render(self, name, value, attrs=None):
        return super(JSONInput, self).render(name, json.dumps(value), attrs)



class NodeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, node):
        return node.node_name

class ReserveIdForm(forms.Form):
    amount = forms.IntegerField(min_value=1, initial=1)
    site = NodeChoiceField(
            queryset=NodeHandle.objects.filter(node_type__type='Site').order_by('node_name'),
            required=False, 
            help_text='If applicable choose a site')
    reserve_message = forms.CharField(help_text='A message to help understand what the reservation was for.', widget=forms.TextInput(attrs={'class': 'input-xxlarge'}))

class SearchIdForm(forms.Form):
    reserved = forms.NullBooleanField(help_text='Choosing "yes" shows avaliable (not in use) IDs', required=False)
    id_type = forms.ChoiceField( required=False)
    site = NodeChoiceField(required=False,
            queryset=NodeHandle.objects.filter(node_type__type='Site').order_by('node_name'))
    reserve_message = forms.CharField(help_text='Search by message', required=False)

    def __init__(self, *args, **kwargs):
        super(SearchIdForm, self).__init__(*args, **kwargs)
        generators = UniqueIdGenerator.objects.all()
        categories = [('','')]
        if generators:
          categories.extend([(g.prefix, g.name.replace("_", " ").title()) for g in generators if g.prefix != ""])
        self.fields['id_type'].choices= categories


class NewSiteForm(forms.Form):
    """
    Concatenate country code with site name
    """
    name = forms.CharField()
    country_code = forms.ChoiceField(choices=COUNTRY_CODES, widget=forms.widgets.Select)
    address = forms.CharField(required=False)
    postarea = forms.CharField(required=False)
    postcode = forms.CharField(required=False)
    
    def clean(self):
        cleaned_data = super(NewSiteForm, self).clean()
        cleaned_data['name'] = '%s-%s' % (cleaned_data['country_code'], cleaned_data['name'].upper())
        cleaned_data['country'] = COUNTRY_MAP[cleaned_data['country_code']]
        return cleaned_data
    
    
class EditSiteForm(forms.Form):
    name = forms.CharField()
    country_code = forms.ChoiceField(choices=COUNTRY_CODES, widget=forms.widgets.Select, required=False)
    country = forms.ChoiceField(choices=COUNTRIES, widget=forms.widgets.Select, required=False)
    site_type = forms.ChoiceField(choices=SITE_TYPES, widget=forms.widgets.Select, required=False)
    address = forms.CharField(required=False)
    floor = forms.CharField(required=False, help_text='Floor of building if applicable.')
    room = forms.CharField(required=False, help_text='Room identifier in building if applicable.')
    postarea = forms.CharField(required=False)
    postcode = forms.CharField(required=False)
    area = forms.CharField(required=False, help_text='State, county or similar.')
    longitude = forms.FloatField(required=False, help_text='Decimal Degrees')
    latitude = forms.FloatField(required=False, help_text='Decimal Degrees')
    telenor_subscription_id = forms.CharField(required=False)
    owner_id = forms.CharField(required=False)
    owner_site_name = forms.CharField(required=False)
    url = forms.URLField(required=False, help_text='An URL to more information about the site.')
    relationship_responsible_for = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)

    def clean(self):
        cleaned_data = super(EditSiteForm, self).clean()
        cleaned_data['name'] = cleaned_data['name'].upper()
        cleaned_data['country_code'] = COUNTRY_CODE_MAP[cleaned_data['country']]
        return cleaned_data
                              
                              
class NewSiteOwnerForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')


class EditSiteOwnerForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')


class NewCableForm(forms.Form):
    name = forms.CharField()
    cable_type = forms.ChoiceField(choices=CABLE_TYPES, widget=forms.widgets.Select)
    relationship_provider = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)


class NewNordunetCableForm(NewCableForm):
    name = forms.CharField(required=False,
                           help_text="If no name is specified the next NORDUnet cable ID will be used.")

    class Meta:
        id_generator_name = 'nordunet_cable_id'
        id_collection = NordunetUniqueId

    def clean(self):
        """
        Sets name to next generated ID or register the name in the ID collection.
        """
        cleaned_data = super(NewNordunetCableForm, self).clean()
        # Set name to a generated id if the cable is not a manually named cable.
        name = cleaned_data.get("name")
        if self.is_valid():
            if not name:
                if not self.Meta.id_generator_name or not self.Meta.id_collection:
                    raise Exception('You have to set id_generator_name and id_collection in form Meta class.')
                try:
                    id_generator = UniqueIdGenerator.objects.get(name=self.Meta.id_generator_name)
                    cleaned_data['name'] = unique_ids.get_collection_unique_id(id_generator, self.Meta.id_collection)
                except UniqueIdGenerator.DoesNotExist as e:
                    raise e
            else:
                try:
                    unique_ids.register_unique_id(self.Meta.id_collection, name)
                except IntegrityError as e:
                    self._errors = ErrorDict()
                    self._errors['name'] = ErrorList()
                    self._errors['name'].append(e.message)
        return cleaned_data

                                       
class EditCableForm(forms.Form):
    name = forms.CharField(help_text='Name will be superseded by Telenor Trunk ID if set.')
    cable_type = forms.ChoiceField(choices=CABLE_TYPES, widget=forms.widgets.Select)
    telenor_tn1_number = forms.CharField(required=False, help_text='Telenor TN1 number, nnnnn.')
    telenor_trunk_id = forms.CharField(required=False, help_text='Telenor Trunk ID, nnn-nnnn.')
    global_crossing_circuit_id = forms.CharField(required=False, help_text='Global Crossing circuit ID, nnnnnnnnnn')
    global_connect_circuit_id = forms.CharField(required=False, help_text='Global Connect circuit ID')
    relationship_end_a = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_end_b = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_provider = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)

    def clean(self):
        cleaned_data = super(EditCableForm, self).clean()
        if cleaned_data.get('telenor_trunk_id', None):
            cleaned_data['name'] = cleaned_data['telenor_trunk_id']
        return cleaned_data


class EditOpticalNodeForm(forms.Form):        
    name = forms.CharField()
    operational_state = forms.ChoiceField(choices=OPERATIONAL_STATES, widget=forms.widgets.Select)
    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
    sites = get_node_type_tuples('Site')
    relationship_ports = JSONField(required=False, widget=JSONInput)
    relationship_location = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
                                              

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
    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
    relationship_parent = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_located_in = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
                
                
class EditHostForm(forms.Form):
    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of what the machine is used for.')
    operational_state = forms.ChoiceField(choices=OPERATIONAL_STATES, widget=forms.widgets.Select)
    #responsible_persons = JSONField(required=False, widget=JSONInput,
    #                                help_text='Name of the person responsible for the host.')
    responsible_group = forms.ChoiceField(choices=RESPONSIBLE_GROUPS, required=False, widget=forms.widgets.Select,
                                          help_text='Name of the group responsible for the host.')
    support_group = forms.ChoiceField(choices=RESPONSIBLE_GROUPS, required=False, widget=forms.widgets.Select,
                                      help_text='Name of the support group.')
    os = forms.CharField(required=False,
                         help_text='What operating system is running on the host?')
    os_version = forms.CharField(required=False,
                                 help_text='Which version of the operating system is running on the host?')
    model = forms.CharField(required=False,
                            help_text='What is the hosts hardware model name?')
    vendor = forms.CharField(required=False,
                             help_text='Name of the vendor that should be contacted for hardware support?')
    service_tag = forms.CharField(required=False, help_text='What is the vendors service tag for the host?')
    end_support = forms.DateField(required=False, help_text='When does the hardware support end?')
    contract_number = forms.CharField(required=False, help_text='Which contract regulates the billing of this host?')
    relationship_location = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_user = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_owner = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_depends_on = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_ports = JSONField(required=False, widget=JSONInput)
    security_class = forms.ChoiceField(required=False, choices=SECURITY_CLASSES, widget=forms.widgets.Select)
    security_comment = forms.CharField(required=False, widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}))
    services_locked = forms.BooleanField(required=False)
    services_checked = forms.BooleanField(required=False)


class EditSwitchForm(EditHostForm):
    max_number_of_ports = forms.IntegerField(help_text='Max number of ports.', required=False)


class EditFirewallForm(EditHostForm):
    max_number_of_ports = forms.IntegerField(help_text='Max number of ports.', required=False)


class EditPDUForm(EditHostForm):
    max_number_of_ports = forms.IntegerField(help_text='Max number of ports.', required=False)


class EditRouterForm(forms.Form):
    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
    operational_state = forms.ChoiceField(choices=OPERATIONAL_STATES, widget=forms.widgets.Select)
    relationship_location = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    
    
class NewOdfForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(NewOdfForm, self).__init__(*args, **kwargs)
        # Set max number of ports to choose from
        max_num_of_ports = 48
        choices = [(x, x) for x in range(1, max_num_of_ports+1) if x]
        self.fields['max_number_of_ports'].choices = choices

    name = forms.CharField()
    max_number_of_ports = forms.ChoiceField(required=False, widget=forms.widgets.Select)


class EditOdfForm(forms.Form):
    name = forms.CharField()
    max_number_of_ports = forms.IntegerField(help_text='Max number of ports.')
    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
    relationship_ports = JSONField(required=False, widget=JSONInput)
    relationship_location = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)


class NewExternalEquipmentForm(forms.Form):
    name = forms.CharField()
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of what the machine is used for.')


class EditExternalEquipmentForm(forms.Form):
    name = forms.CharField()
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of what the machine is used for.')
    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
    relationship_owner = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_ports = JSONField(required=False, widget=JSONInput)
    relationship_location = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)


class NewPortForm(forms.Form):
    name = forms.CharField()
    port_type = forms.ChoiceField(required=False, choices=PORT_TYPES, widget=forms.widgets.Select)
    relationship_parent = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)


class EditPortForm(forms.Form):
    name = forms.CharField()
    port_type = forms.ChoiceField(required=False, choices=PORT_TYPES, widget=forms.widgets.Select)
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Notes regarding port usage.')
    relationship_parent = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)


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
    def __init__(self, *args, **kwargs):
        super(NewServiceForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')

    name = forms.CharField(required=False,
                           help_text='Name will only be available for manually named service types.')
    service_class = forms.CharField(required=False, widget=forms.widgets.HiddenInput)
    service_type = forms.ChoiceField(choices=SERVICE_TYPES, widget=forms.widgets.Select)
    operational_state = forms.ChoiceField(choices=OPERATIONAL_STATES, widget=forms.widgets.Select)
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of the service.')
    responsible_group = forms.ChoiceField(choices=RESPONSIBLE_GROUPS, required=False, widget=forms.widgets.Select,
                                          help_text='Name of the group responsible for the service.')
    support_group = forms.ChoiceField(choices=RESPONSIBLE_GROUPS, required=False, widget=forms.widgets.Select,
                                      help_text='Name of the support group.')
    relationship_provider = forms.ChoiceField(required=False, widget=forms.widgets.Select)

    class Meta:
        id_generator_name = None                # UniqueIdGenerator instance name
        id_collection = None                    # Subclass of UniqueId
        manually_named_services = ['External']  # service_type of manually named services

    def clean(self):
        """
        Sets name to next service ID for internal services. Only expect a user
        inputted name for manually named services.
        Sets the service class from the service type.
        """
        cleaned_data = super(NewServiceForm, self).clean()
        # Set name to a generated id if the service is not a manually named service.
        name = cleaned_data.get("name")
        service_type = cleaned_data.get("service_type")
        if self.is_valid():
            if not name and service_type not in self.Meta.manually_named_services:
                if not self.Meta.id_generator_name or not self.Meta.id_collection:
                    raise Exception('You have to set id_generator_name and id_collection in form Meta class.')
                try:
                    id_generator = UniqueIdGenerator.objects.get(name=self.Meta.id_generator_name)
                    cleaned_data['name'] = unique_ids.get_collection_unique_id(id_generator, self.Meta.id_collection)
                except UniqueIdGenerator.DoesNotExist as e:
                    raise e
            elif not name:
                self._errors = ErrorDict()
                self._errors['name'] = ErrorList()
                self._errors['name'].append('Missing name for %s service.' % service_type)
        # Set service_class depending on service_type.
        cleaned_data['service_class'] = SERVICE_CLASS_MAP[self.cleaned_data['service_type']]
        return cleaned_data


class NewNordunetServiceForm(NewServiceForm):

    project_end_date = forms.DateField(required=False)

    class Meta(NewServiceForm.Meta):
        id_generator_name = 'nordunet_service_id'
        id_collection = NordunetUniqueId

    def clean(self):
        """
        Checks that project_end_date was not omitted if service is of type project.
        """
        cleaned_data = super(NewNordunetServiceForm, self).clean()
        if cleaned_data['service_type'] == 'Project' and not cleaned_data['project_end_date']:
            self._errors = ErrorDict()
            self._errors['project_end_date'] = ErrorList()
            self._errors['project_end_date'].append('Missing project end date.')
        # Convert  project_end_date to string if set
        if cleaned_data.get('project_end_date', None):
            cleaned_data['project_end_date'] = cleaned_data['project_end_date'].strftime('%Y-%m-%d')
        return cleaned_data


class NewNordunetL2vpnServiceForm(NewNordunetServiceForm):

    ncs_service_name = forms.CharField(required=False, help_text='')
    vpn_type = forms.CharField(required=False, help_text='')
    vlan = forms.CharField(required=False, help_text='')
    vrf_target = forms.CharField(required=False, help_text='')
    route_distinguisher = forms.CharField(required=False, help_text='')


class EditServiceForm(forms.Form):
    name = forms.CharField(required=False)
    service_class = forms.CharField(required=False, widget=forms.widgets.HiddenInput)
    service_type = forms.ChoiceField(choices=SERVICE_TYPES,
                                     widget=forms.widgets.Select)
    project_end_date = forms.DateField(required=False)
    decommissioned_date = forms.DateField(required=False)
    operational_state = forms.ChoiceField(choices=OPERATIONAL_STATES,
                                          widget=forms.widgets.Select)
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of the service.')
    responsible_group = forms.ChoiceField(choices=RESPONSIBLE_GROUPS, required=False, widget=forms.widgets.Select,
                                          help_text='Name of the group responsible for the service.')
    support_group = forms.ChoiceField(choices=RESPONSIBLE_GROUPS, required=False, widget=forms.widgets.Select,
                                      help_text='Name of the support group.')
    ncs_service_name = forms.CharField(required=False, help_text='')
    vpn_type = forms.CharField(required=False, help_text='')
    vlan = forms.CharField(required=False, help_text='')
    vrf_target = forms.CharField(required=False, help_text='')
    route_distinguisher = forms.CharField(required=False, help_text='')
    contract_number = forms.CharField(required=False, help_text='Which contract regulates the billing of this service?')
    relationship_provider = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_user = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_depends_on = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)

    def clean(self):
        cleaned_data = super(EditServiceForm, self).clean()
        # Set service_class depending on service_type.
        cleaned_data['service_class'] = SERVICE_CLASS_MAP[self.cleaned_data['service_type']]
        # Check that project_end_date is filled in for Project service type
        if cleaned_data['service_type'] == 'Project' and not cleaned_data['project_end_date']:
            self._errors = ErrorDict()
            self._errors['project_end_date'] = ErrorList()
            self._errors['project_end_date'].append('Missing project end date.')
        if cleaned_data.get('operational_state', None):
            # Check that decommissioned_date is filled in for operational state Decommissioned
            if cleaned_data['operational_state'] == 'Decommissioned':
                if not cleaned_data.get('decommissioned_date', None):
                    cleaned_data['decommissioned_date'] = datetime.today()
            else:
                cleaned_data['decommissioned_date'] = None
        else:
            self._errors = ErrorDict()
            self._errors['operational_state'] = ErrorList()
            self._errors['operational_state'].append('Missing operational state.')
        # Convert  project_end_date to string if set
        if cleaned_data.get('project_end_date', None):
            cleaned_data['project_end_date'] = cleaned_data['project_end_date'].strftime('%Y-%m-%d')
        # Convert decommissioned_date to string if set
        if cleaned_data.get('decommissioned_date', None):
            cleaned_data['decommissioned_date'] = cleaned_data['decommissioned_date'].strftime('%Y-%m-%d')
        return cleaned_data


class NewOpticalLinkForm(forms.Form):
    name = forms.CharField(required=False, widget=forms.widgets.HiddenInput)
    link_type = forms.ChoiceField(choices=OPTICAL_LINK_TYPES, widget=forms.widgets.Select)
    interface_type = forms.ChoiceField(choices=OPTICAL_LINK_INTERFACE_TYPE)
    operational_state = forms.ChoiceField(choices=OPERATIONAL_STATES, widget=forms.widgets.Select)
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of the optical link.')
    relationship_provider = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)

    class Meta:
        id_generator_name = None    # UniqueIdGenerator instance name
        id_collection = None        # Subclass of UniqueId

    def clean(self):
        """
        Sets name to next generated ID.
        """
        cleaned_data = super(NewOpticalLinkForm, self).clean()
        # Set name to a generated id if the service is not a manually named service.
        name = cleaned_data.get("name")
        if not name and self.is_valid():
            if not self.Meta.id_generator_name or not self.Meta.id_collection:
                raise Exception('You have to set id_generator_name and id_collection in form Meta class.')
            try:
                id_generator = UniqueIdGenerator.objects.get(name=self.Meta.id_generator_name)
                cleaned_data['name'] = unique_ids.get_collection_unique_id(id_generator, self.Meta.id_collection)
            except UniqueIdGenerator.DoesNotExist as e:
                raise e
        return cleaned_data


class NewNordunetOpticalLinkForm(NewOpticalLinkForm):

    class Meta(NewOpticalLinkForm.Meta):
        id_generator_name = 'nordunet_optical_link_id'
        id_collection = NordunetUniqueId

    def clean(self):
        cleaned_data = super(NewNordunetOpticalLinkForm, self).clean()
        return cleaned_data


class EditOpticalLinkForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(EditOpticalLinkForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')

    link_type = forms.ChoiceField(choices=OPTICAL_LINK_TYPES,
                                  widget=forms.widgets.Select)
    interface_type = forms.ChoiceField(choices=OPTICAL_LINK_INTERFACE_TYPE)
    operational_state = forms.ChoiceField(choices=OPERATIONAL_STATES,
                                          widget=forms.widgets.Select)
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of the optical link.')
    relationship_provider = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_end_a = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_end_b = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)


class NewOpticalMultiplexSectionForm(forms.Form):
    name = forms.CharField(help_text='Naming should be derived from the end equipment names, equipment1-equipment2.')
    operational_state = forms.ChoiceField(choices=OPERATIONAL_STATES, widget=forms.widgets.Select)
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of the optical link.')
    relationship_provider = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)


class EditOpticalMultiplexSectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(EditOpticalMultiplexSectionForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')
        self.fields['relationship_depends_on'].choices = get_node_type_tuples('Optical Link')

    name = forms.CharField(help_text='Naming should be derived from the end equipment names, equipment1-equipment2.')
    operational_state = forms.ChoiceField(choices=OPERATIONAL_STATES,
                                          widget=forms.widgets.Select)
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of the optical path.')
    relationship_provider = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_depends_on = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)


class NewOpticalPathForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(NewOpticalPathForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')

    name = forms.CharField(required=False, widget=forms.widgets.HiddenInput)
    framing = forms.ChoiceField(choices=OPTICAL_PATH_FRAMING,
                                widget=forms.widgets.Select)
    capacity = forms.ChoiceField(choices=OPTICAL_PATH_CAPACITY,
                                 widget=forms.widgets.Select)
    operational_state = forms.ChoiceField(choices=OPERATIONAL_STATES,
                                          widget=forms.widgets.Select)
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of the optical path.')
    relationship_provider = forms.ChoiceField(required=False, widget=forms.widgets.Select)

    class Meta:
        id_generator_name = None    # UniqueIdGenerator instance name
        id_collection = None        # Subclass of UniqueId

    def clean(self):
        """
        Sets name to next generated ID.
        """
        cleaned_data = super(NewOpticalPathForm, self).clean()
        # Set name to a generated id if the service is not a manually named service.
        name = cleaned_data.get("name")
        if not name and self.is_valid():
            if not self.Meta.id_generator_name or not self.Meta.id_collection:
                raise Exception('You have to set id_generator_name and id_collection in form Meta class.')
            try:
                id_generator = UniqueIdGenerator.objects.get(name=self.Meta.id_generator_name)
                cleaned_data['name'] = unique_ids.get_collection_unique_id(id_generator, self.Meta.id_collection)
            except UniqueIdGenerator.DoesNotExist as e:
                raise e
        return cleaned_data


class NewNordunetOpticalPathForm(NewOpticalPathForm):

    class Meta(NewOpticalLinkForm.Meta):
        id_generator_name = 'nordunet_optical_path_id'
        id_collection = NordunetUniqueId

    def clean(self):
        cleaned_data = super(NewNordunetOpticalPathForm, self).clean()
        return cleaned_data


class EditOpticalPathForm(forms.Form):
    framing = forms.ChoiceField(choices=OPTICAL_PATH_FRAMING,
                                widget=forms.widgets.Select)
    capacity = forms.ChoiceField(choices=OPTICAL_PATH_CAPACITY,
                                 widget=forms.widgets.Select)
    operational_state = forms.ChoiceField(choices=OPERATIONAL_STATES,
                                          widget=forms.widgets.Select)
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                                  help_text='Short description of the optical path.')
    enrs = JSONField(required=False, widget=JSONInput)
    relationship_provider = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_depends_on = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
