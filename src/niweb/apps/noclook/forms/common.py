from datetime import datetime
from django import forms
from django.forms.utils import ErrorDict, ErrorList, ValidationError
from django.forms.widgets import HiddenInput, Textarea
from django.db import IntegrityError
import json
import csv
from apps.noclook import helpers
from apps.noclook.models import NodeType, NodeHandle, RoleGroup, Role,\
                                UniqueIdGenerator, ServiceType,\
                                NordunetUniqueId, Dropdown, DEFAULT_ROLES,\
                                DEFAULT_ROLE_KEY, DEFAULT_ROLEGROUP_NAME

from .validators import *
from .. import unique_ids
import norduniclient as nc
from dynamic_preferences.registries import global_preferences_registry
from django.utils import six
from io import StringIO
import ipaddress


# We should move this kind of data to the SQL database.
def country_codes():
    codes = Dropdown.get('countries').as_values()
    return zip(codes, codes)


def email_choices():
    return Dropdown.get('email_type').as_choices()


def phone_choices():
    return Dropdown.get('phone_type').as_choices()


def countries():
    choices = Dropdown.get('countries').as_choices()
    codes, countries = zip(*choices)
    return zip(countries, countries)


def country_map(country_code):
    return dict(Dropdown.get('countries').as_choices(False)).get(country_code, '')


def country_code_map(country):
    return {k: v for v, k in Dropdown.get('countries').as_choices(False)}.get(country, '')


def get_node_type_tuples(node_type):
    """
    Returns a list of tuple of node.handle_id and node['name'] of label node_type.
    """
    choices = [('', '')]
    q = """
        MATCH (n:{node_type})
        RETURN n.handle_id as handle_id, n.name as name
        ORDER BY n.name
        """.format(node_type=node_type.replace(' ', '_'))
    l = nc.query_to_list(nc.graphdb.manager, q)
    choices.extend([tuple([item['handle_id'], item['name']]) for item in l])
    return choices


def get_contacts_for_organization(organization_id):
    """
    Returns a list of tuple of node.handle_id and node['name'] of contacts that
    works for a certain organization
    """
    organization = NodeHandle.objects.get(handle_id=organization_id)
    contacts = organization.get_node().get_contacts()

    return _get_tuples_for_iterator(contacts)


def _get_tuples_for_iterator(iterator):
    """
    Returns a list of tuple of handle_id and name of iterator.
    """
    choices = [('', '')]
    choices.extend([tuple([item['handle_id'], item['name']]) for item in iterator])
    return choices


class IPAddrField(forms.CharField):
    def __init__(self, *args, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = forms.Textarea(attrs={'cols': '120', 'rows': '3'})
        super(IPAddrField, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = super(IPAddrField, self).clean(value)
        errors = []
        result = []
        for line in StringIO(value):
            ip = line.replace('\n','').strip()
            if ip:
                try:
                    ipaddress.ip_address(ip)
                    result.append(ip)
                except ValueError as e:
                    errors.append(str(e))
        if errors:
            raise ValidationError(errors)
        return result

    def prepare_value(self, value):
        if isinstance(value, list):
            value = u'\n'.join(value)
        return super(IPAddrField, self).prepare_value(value)


    def to_python(self, value):
        if isinstance(value, list):
            value = u'\n'.join(value)
        return super(IPAddrField, self).to_python(value)


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


class DatePickerField(forms.DateField):
    def __init__(self, *args, **kwargs):
        attrs = {'data-provide': 'datepicker', 'data-date-format': 'yyyy-mm-dd', 'data-date-today-highlight': 'true'}
        if kwargs.get('today'):
            attrs['data-date-today-btn'] = 'linked'
            del kwargs['today']
        super(DatePickerField, self).__init__(*args, **kwargs)
        self.widget = forms.TextInput(attrs=attrs)


def description_field(name):
    return forms.CharField(required=False,
                           widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                           help_text=u'Short description of the {}.'.format(name))


def relationship_field(name, select=False, validators=[]):
    labels = {
    }
    label = labels.get(name, name.title())
    if select:
        return forms.ChoiceField(required=False, label=label, widget=forms.widgets.Select, validators=[])
    else:
        return forms.IntegerField(required=False, label=label, widget=forms.widgets.HiddenInput, validators=[])


class ReserveIdForm(forms.Form):
    amount = forms.IntegerField(min_value=1, initial=1)
    site = NodeChoiceField(
        queryset=NodeHandle.objects.filter(node_type__type='Site').order_by('node_name'),
        required=False,
        help_text='If applicable choose a site')
    reserve_message = forms.CharField(help_text='A message to help understand what the reservation was for.', widget=forms.TextInput(attrs={'class': 'input-xxlarge'}))


class SearchIdForm(forms.Form):
    reserved = forms.NullBooleanField(help_text='Choosing "yes" shows avaliable (not in use) IDs', required=False)
    id_type = forms.ChoiceField(required=False)
    site = NodeChoiceField(required=False,
                           queryset=NodeHandle.objects.filter(node_type__type='Site').order_by('node_name'))
    reserve_message = forms.CharField(help_text='Search by message', required=False)

    def __init__(self, *args, **kwargs):
        super(SearchIdForm, self).__init__(*args, **kwargs)
        generators = UniqueIdGenerator.objects.all()
        categories = [('', '')]
        if generators:
            categories.extend([(g.prefix, g.name.replace("_", " ").title()) for g in generators if g.prefix != ""])
        self.fields['id_type'].choices = categories


class NewSiteForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(NewSiteForm, self).__init__(*args, **kwargs)
        self.fields['country_code'].choices = country_codes()

    name = forms.CharField()
    country_code = forms.ChoiceField(widget=forms.widgets.Select)
    country = forms.CharField(required=False, widget=forms.widgets.HiddenInput)
    address = forms.CharField(required=False)
    postarea = forms.CharField(required=False)
    postcode = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super(NewSiteForm, self).clean()
        cleaned_data['country'] = country_map(cleaned_data['country_code'])
        return cleaned_data


class EditSiteForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(EditSiteForm, self).__init__(*args, **kwargs)
        self.fields['country_code'].choices = country_codes()
        self.fields['country'].choices = countries()
        self.fields['site_type'].choices = Dropdown.get('site_types').as_choices()
        self.fields['relationship_responsible_for'].choices = get_node_type_tuples('Site_Owner')

    name = forms.CharField()
    country_code = forms.ChoiceField(widget=forms.widgets.Select, required=False)
    country = forms.ChoiceField(widget=forms.widgets.Select, required=False)
    site_type = forms.ChoiceField(widget=forms.widgets.Select, required=False)
    address = forms.CharField(required=False, label='Street')
    floor = forms.CharField(required=False, help_text='Floor of building if applicable.')
    room = forms.CharField(required=False, help_text='Room identifier in building if applicable.')
    postarea = forms.CharField(required=False)
    postcode = forms.CharField(required=False)
    area = forms.CharField(required=False, help_text='State, county or similar.')
    longitude = forms.FloatField(required=False, help_text='Decimal Degrees')
    latitude = forms.FloatField(required=False, help_text='Decimal Degrees')
    telenor_subscription_id = forms.CharField(required=False, label='Telenor subscription ID')
    owner_id = forms.CharField(required=False, label='Owner site ID')
    owner_site_name = forms.CharField(required=False)
    url = forms.URLField(required=False, help_text='An URL to more information about the site.', label='Information URL')
    relationship_responsible_for = relationship_field('responsible', True)

    def clean(self):
        cleaned_data = super(EditSiteForm, self).clean()
        cleaned_data['name'] = cleaned_data['name']
        cleaned_data['country_code'] = country_code_map(cleaned_data['country'])
        return cleaned_data


class NewSiteOwnerForm(forms.Form):
    name = forms.CharField()
    description = description_field('site owner')
    url = forms.URLField(required=False, help_text='Link to more information.')


class EditSiteOwnerForm(NewSiteOwnerForm):
    pass


class NewCableForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(NewCableForm, self).__init__(*args, **kwargs)
        self.fields['cable_type'].choices = Dropdown.get('cable_types').as_choices()
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')

    name = forms.CharField()
    cable_type = forms.ChoiceField(widget=forms.widgets.Select)
    description = description_field('cable')
    relationship_provider = relationship_field('provider', True)


class EditCableForm(NewCableForm):
    relationship_end_a = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_end_b = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)


class OpticalNodeForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(OpticalNodeForm, self).__init__(*args, **kwargs)
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()
        self.fields['type'].choices = Dropdown.get('optical_node_types').as_choices()
    name = forms.CharField()
    type = forms.ChoiceField()
    operational_state = forms.ChoiceField(initial='In service')
    description = description_field('optical node')
    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
    rack_position = forms.IntegerField(required=False, help_text='Where in the rack is this located.')
    relationship_location = relationship_field('location')


class EditOpticalNodeForm(OpticalNodeForm):
    relationship_ports = JSONField(required=False, widget=JSONInput)


class EditPeeringPartnerForm(forms.Form):
    name = forms.CharField()


class EditPeeringGroupForm(forms.Form):
    name = forms.CharField()


class NewRackForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(NewRackForm, self).__init__(*args, **kwargs)
        self.fields['relationship_location'].choices = get_node_type_tuples('Site')

    name = forms.CharField(help_text='Name should be the grid location.')
    relationship_location = relationship_field('location', True)


class EditRackForm(forms.Form):
    name = forms.CharField(help_text='Name should be the site grid location.')
    height = forms.IntegerField(required=False,
                                help_text='Height in millimeters (mm).')
    depth = forms.IntegerField(required=False,
                               help_text='Depth in millimeters (mm).')
    width = forms.IntegerField(required=False,
                               help_text='Width in millimeters (mm).')
    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
    relationship_parent = relationship_field('parent')
    relationship_located_in = relationship_field('located in')


class NewHostForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(NewHostForm, self).__init__(*args, **kwargs)
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()
        self.fields['responsible_group'].choices = Dropdown.get('responsible_groups').as_choices()
        self.fields['support_group'].choices = Dropdown.get('responsible_groups').as_choices()
        self.fields['security_class'].choices = Dropdown.get('security_classes').as_choices()
        self.fields['managed_by'].choices = Dropdown.get('host_management_sw').as_choices()

    name = forms.CharField(help_text="The hostname")
    ip_addresses = IPAddrField(help_text="One ip per line", required=False)
    rack_units = forms.IntegerField(required=False,
                                    label='Equipment height',
                                    help_text='Height in rack units (u).')
    rack_position = forms.IntegerField(required=False, help_text='Where in the rack is this located.')
    description = description_field('machine and what it is used for')
    operational_state = forms.ChoiceField(widget=forms.widgets.Select, initial='In service')
    managed_by = forms.ChoiceField(required=False, widget=forms.widgets.Select,
                                   help_text='Name of the management software that manages the host')

    responsible_group = forms.ChoiceField(required=False, widget=forms.widgets.Select,
                                          help_text='Name of the group responsible for the host.')
    support_group = forms.ChoiceField(required=False, widget=forms.widgets.Select,
                                      help_text='Name of the support group.')
    backup = forms.CharField(required=False, help_text='Which backup solution is used? e.g. TSM, IP nett?')
    security_class = forms.ChoiceField(required=False, widget=forms.widgets.Select)
    security_comment = forms.CharField(required=False, widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}))
    os = forms.CharField(required=False,
                         label='Operating system',
                         help_text='What operating system is running on the host?')
    os_version = forms.CharField(required=False,
                                 label='Operating system version',
                                 help_text='Which version of the operating system is running on the host?')
    model = forms.CharField(required=False,
                            label='Hardware model',
                            help_text='What is the hosts hardware model name?')
    vendor = forms.CharField(required=False,
                             help_text='Name of the vendor that should be contacted for hardware support?')
    service_tag = forms.CharField(required=False, help_text='What is the vendors service tag for the host?')
    end_support = DatePickerField(required=False,
                                  label='End of support',
                                  help_text='When does the hardware support end?')
    contract_number = forms.CharField(required=False, help_text='Which contract regulates the billing of this host?')
    # External relations
    relationship_location = relationship_field('location')
    relationship_owner = relationship_field('owner')


class EditHostForm(NewHostForm):
    relationship_user = relationship_field('user')
    relationship_depends_on = relationship_field('depends on')
    relationship_ports = JSONField(required=False, widget=JSONInput)

    services_locked = forms.BooleanField(required=False)
    services_checked = forms.BooleanField(required=False)


class EditSwitchForm(EditHostForm):
    max_number_of_ports = forms.IntegerField(help_text='Max number of ports.', required=False)


class EditFirewallForm(EditHostForm):
    max_number_of_ports = forms.IntegerField(help_text='Max number of ports.', required=False)


class EditPDUForm(EditHostForm):
    max_number_of_ports = forms.IntegerField(help_text='Max number of ports.', required=False)


class EditRouterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(EditRouterForm, self).__init__(*args, **kwargs)
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()

    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
    rack_position = forms.IntegerField(required=False, help_text='Where in the rack is this located.')
    operational_state = forms.ChoiceField(widget=forms.widgets.Select)
    relationship_location = relationship_field('location')
    relationship_ports = JSONField(required=False, widget=JSONInput)
    description = description_field('router')


class NewOdfForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(NewOdfForm, self).__init__(*args, **kwargs)
        # Set max number of ports to choose from
        max_num_of_ports = 48
        choices = [(x, x) for x in range(1, max_num_of_ports + 1) if x]
        self.fields['max_number_of_ports'].choices = choices
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()

    name = forms.CharField()
    description = description_field('ODF')
    max_number_of_ports = forms.ChoiceField(required=False, widget=forms.widgets.Select)
    operational_state = forms.ChoiceField(required=False, widget=forms.widgets.Select)
    relationship_location = relationship_field('location')
    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
    rack_position = forms.IntegerField(required=False, help_text='Where in the rack is this located.')


class BulkPortsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(BulkPortsForm, self).__init__(*args, **kwargs)
        self.fields['port_type'].choices = Dropdown.get('port_types').as_choices()

    no_ports = forms.BooleanField(required=False, help_text='Do not create any ports')
    bundled = forms.BooleanField(required=False, help_text='Bundle the ports e.g 1+2, 2+3 (half the ports)')
    port_type = forms.ChoiceField(required=False)
    prefix = forms.CharField(required=False, help_text='Port prefix e.g. ge-1/0')
    offset = forms.IntegerField(required=False, min_value=0, initial=1)
    num_ports = forms.IntegerField(required=False, min_value=0, initial=0)


class EditOdfForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(EditOdfForm, self).__init__(*args, **kwargs)
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()

    name = forms.CharField()
    description = description_field('ODF')
    max_number_of_ports = forms.IntegerField(required=False, help_text='Max number of ports.')
    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
    rack_position = forms.IntegerField(required=False, help_text='Where in the rack is this located.')
    operational_state = forms.ChoiceField(required=False, widget=forms.widgets.Select)
    relationship_ports = JSONField(required=False, widget=JSONInput)
    relationship_location = relationship_field('location')


class NewOpticalFilter(NewOdfForm):
    pass


class EditOpticalFilterForm(EditOdfForm):
    pass


class NewExternalEquipmentForm(forms.Form):
    name = forms.CharField()

    description = description_field('external equipment')
    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
    rack_position = forms.IntegerField(required=False, help_text='Where in the rack is this located.')
    relationship_owner = relationship_field('owner')
    relationship_location = relationship_field('location')


class EditExternalEquipmentForm(NewExternalEquipmentForm):
    relationship_ports = JSONField(required=False, widget=JSONInput)


class NewPortForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(NewPortForm, self).__init__(*args, **kwargs)
        self.fields['port_type'].choices = Dropdown.get('port_types').as_choices()

    name = forms.CharField()
    port_type = forms.ChoiceField(required=False, widget=forms.widgets.Select)
    description = description_field('port usage')
    relationship_parent = relationship_field('parent')


class EditPortForm(NewPortForm):
    relationship_connected_to = relationship_field('connected to')


class NewCustomerForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}))


class EditCustomerForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}))


class NewEndUserForm(forms.Form):
    name = forms.CharField()
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}))
    url = forms.URLField(required=False, help_text='Link to more information.')


class EditEndUserForm(NewEndUserForm):
    pass


class NewProviderForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')


class EditProviderForm(forms.Form):
    name = forms.CharField()
    url = forms.URLField(required=False, help_text='Link to more information.')


class NewServiceForm(forms.Form):

    name = forms.CharField(required=False, help_text='Name will only be available for manually named service types.')
    service_class = forms.CharField(required=False, widget=forms.widgets.HiddenInput)
    service_type = forms.ChoiceField(widget=forms.widgets.Select)
    operational_state = forms.ChoiceField(widget=forms.widgets.Select)
    description = description_field('service')
    responsible_group = forms.ChoiceField(required=False, widget=forms.widgets.Select,
                                          help_text='Name of the group responsible for the service.')
    support_group = forms.ChoiceField(required=False, widget=forms.widgets.Select,
                                      help_text='Name of the support group.')
    relationship_provider = relationship_field('provider', True)

    def __init__(self, *args, **kwargs):
        super(NewServiceForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()
        self.fields['responsible_group'].choices = Dropdown.get('responsible_groups').as_choices()
        self.fields['support_group'].choices = Dropdown.get('responsible_groups').as_choices()
        service_types = ServiceType.objects.all().prefetch_related('service_class').order_by('service_class__name', 'name')
        self.fields['service_type'].choices = [t.as_choice() for t in service_types]

    class Meta:
        id_generator_property = 'id_generators__services'
        manually_named_services = ['External']  # service_type of manually named services
        manually_named_services_class = ['External']

    def clean(self):
        """
        Sets name to next service ID for internal services. Only expect a user
        inputted name for manually named services.
        Sets the service class from the service type.
        """
        cleaned_data = super(NewServiceForm, self).clean()
        # Set service_class depending on service_type.
        service_type_ = ServiceType.objects.get(name=cleaned_data.get('service_type'))
        cleaned_data['service_class'] = service_type_.service_class.name
        # Set name to a generated id if the service is not a manually named service.
        name = cleaned_data.get("name")
        service_type = cleaned_data.get("service_type")
        if self.is_valid():
            is_maunal_name = service_type in self.Meta.manually_named_services or cleaned_data['service_class'] in self.Meta.manually_named_services_class
            if not name and not is_maunal_name:
                try:
                    global_preferences = global_preferences_registry.manager()
                    id_generator_name = global_preferences[self.Meta.id_generator_property]
                    id_generator = UniqueIdGenerator.objects.get(name=id_generator_name)
                    # id_collection is always the same so we do not need config
                    cleaned_data['name'] = unique_ids.get_collection_unique_id(id_generator, NordunetUniqueId)
                except UniqueIdGenerator.DoesNotExist:
                    msg = u'UniqueIdGenerator with the name "{}" does not exist'.format(id_generator_name)
                    raise UniqueIdGenerator.DoesNotExist(msg)
            elif not name:
                self.add_error('name', 'Missing name for {} service.'.format(service_type))
        return cleaned_data


class EditServiceForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(EditServiceForm, self).__init__(*args, **kwargs)
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()
        self.fields['responsible_group'].choices = Dropdown.get('responsible_groups').as_choices()
        self.fields['support_group'].choices = Dropdown.get('responsible_groups').as_choices()
        service_types = ServiceType.objects.all().prefetch_related('service_class').order_by('service_class__name','name')
        self.fields['service_type'].choices = [t.as_choice() for t in service_types]
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')

    name = forms.CharField(required=False)
    service_class = forms.CharField(required=False, widget=forms.widgets.HiddenInput)
    service_type = forms.ChoiceField(widget=forms.widgets.Select)
    project_end_date = DatePickerField(required=False)
    decommissioned_date = DatePickerField(required=False, today=True)
    operational_state = forms.ChoiceField(widget=forms.widgets.Select)
    description = description_field('service')
    responsible_group = forms.ChoiceField(required=False, widget=forms.widgets.Select,
                                          help_text='Name of the group responsible for the service.')
    support_group = forms.ChoiceField(required=False, widget=forms.widgets.Select,
                                      help_text='Name of the support group.')
    ncs_service_name = forms.CharField(required=False, help_text='')
    vpn_type = forms.CharField(required=False, help_text='')
    vlan = forms.CharField(required=False, help_text='')
    vrf_target = forms.CharField(required=False, help_text='')
    route_distinguisher = forms.CharField(required=False, help_text='')
    contract_number = forms.CharField(required=False, help_text='Which contract regulates the billing of this service?')
    relationship_provider = relationship_field('provider', True)
    relationship_user = relationship_field('user')
    relationship_depends_on = relationship_field('depends on')

    def clean(self):
        cleaned_data = super(EditServiceForm, self).clean()
        # Set service_class depending on service_type.
        #TODO: Handle when service type does not exist?
        service_type_ = ServiceType.objects.get(name=cleaned_data.get('service_type'))
        cleaned_data['service_class'] = service_type_.service_class.name
        # Check that project_end_date is filled in for Project service type
        if cleaned_data['service_type'] == 'Project' and not cleaned_data['project_end_date']:
            self.add_error('project_end_date', 'Missing project end date.')
        if cleaned_data.get('operational_state', None):
            # Check that decommissioned_date is filled in for operational state Decommissioned
            if cleaned_data['operational_state'] == 'Decommissioned':
                if not cleaned_data.get('decommissioned_date', None):
                    cleaned_data['decommissioned_date'] = datetime.today()
            else:
                cleaned_data['decommissioned_date'] = None
        else:
            self.add_error('operational_state', 'Missing operational state.')
        # Convert  project_end_date to string if set
        if cleaned_data.get('project_end_date', None):
            cleaned_data['project_end_date'] = cleaned_data['project_end_date'].strftime('%Y-%m-%d')
        # Convert decommissioned_date to string if set
        if cleaned_data.get('decommissioned_date', None):
            cleaned_data['decommissioned_date'] = cleaned_data['decommissioned_date'].strftime('%Y-%m-%d')
        return cleaned_data


class NewOpticalLinkForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(NewOpticalLinkForm, self).__init__(*args, **kwargs)
        self.fields['link_type'].choices = Dropdown.get('optical_link_types').as_choices()
        self.fields['interface_type'].choices = Dropdown.get('optical_link_interface_type').as_choices()
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')

    name = forms.CharField(required=True)
    link_type = forms.ChoiceField(widget=forms.widgets.Select)
    interface_type = forms.ChoiceField(widget=forms.widgets.Select)
    operational_state = forms.ChoiceField(widget=forms.widgets.Select)
    description = description_field('optical link')
    relationship_provider = relationship_field('provider', True)

    class Meta:
        id_generator_name = None    # UniqueIdGenerator instance name
        id_collection = None        # Subclass of UniqueId

    def clean(self):
        """
        Sets name to next generated ID.
        """
        cleaned_data = super(NewOpticalLinkForm, self).clean()
        # Set name to a generated id if the name is not supplied
        name = cleaned_data.get("name")
        if not name and self.is_valid():
            if not self.Meta.id_generator_name or not self.Meta.id_collection:
                raise Exception('You have to set id_generator_name and id_collection in form Meta class.')
            try:
                id_generator = UniqueIdGenerator.objects.get(name=self.Meta.id_generator_name)
                cleaned_data['name'] = unique_ids.get_collection_unique_id(id_generator, self.Meta.id_collection)
            except UniqueIdGenerator.DoesNotExist as e:
                raise e
        elif self.Meta.id_collection:
            try:
                unique_ids.register_unique_id(self.Meta.id_collection, name)
            except IntegrityError as e:
                self.add_error('name', str(e))
        return cleaned_data


class EditOpticalLinkForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(EditOpticalLinkForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')
        self.fields['link_type'].choices = Dropdown.get('optical_link_types').as_choices()
        self.fields['interface_type'].choices = Dropdown.get('optical_link_interface_type').as_choices()
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()

    name = forms.CharField(required=True)
    link_type = forms.ChoiceField(widget=forms.widgets.Select)
    interface_type = forms.ChoiceField(widget=forms.widgets.Select)
    operational_state = forms.ChoiceField(widget=forms.widgets.Select)
    description = description_field('optical link')
    relationship_provider = relationship_field('provider', True)
    relationship_end_a = relationship_field('Choose end A')
    relationship_end_b = relationship_field('Choose end B')


class NewOpticalMultiplexSectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(NewOpticalMultiplexSectionForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()

    name = forms.CharField(help_text='Naming should be derived from the end equipment names, equipment1-equipment2.')
    operational_state = forms.ChoiceField(widget=forms.widgets.Select)
    description = description_field('optical link')
    relationship_provider = relationship_field('provider', True)


class EditOpticalMultiplexSectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(EditOpticalMultiplexSectionForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')
        self.fields['relationship_depends_on'].choices = get_node_type_tuples('Optical Link')
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()

    name = forms.CharField(help_text='Naming should be derived from the end equipment names, equipment1-equipment2.')
    operational_state = forms.ChoiceField(widget=forms.widgets.Select)
    description = description_field('optical path')
    relationship_provider = relationship_field('provider', True)
    relationship_depends_on = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput, label='Depends on')


class NewOpticalPathForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(NewOpticalPathForm, self).__init__(*args, **kwargs)
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')
        self.fields['framing'].choices = Dropdown.get('optical_path_framing').as_choices()
        self.fields['capacity'].choices = Dropdown.get('optical_path_capacity').as_choices()
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()

    name = forms.CharField(required=True)
    framing = forms.ChoiceField(widget=forms.widgets.Select)
    capacity = forms.ChoiceField(widget=forms.widgets.Select)
    wavelength = forms.IntegerField(required=False, help_text='Measured in GHz')
    operational_state = forms.ChoiceField(widget=forms.widgets.Select)
    description = description_field('optical path')
    relationship_provider = relationship_field('provider', True)

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
        elif self.Meta.id_collection:
            try:
                unique_ids.register_unique_id(self.Meta.id_collection, name)
            except IntegrityError as e:
                self.add_error('name', str(e))
        return cleaned_data


class EditOpticalPathForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(EditOpticalPathForm, self).__init__(*args, **kwargs)
        self.fields['framing'].choices = Dropdown.get('optical_path_framing').as_choices()
        self.fields['capacity'].choices = Dropdown.get('optical_path_capacity').as_choices()
        self.fields['operational_state'].choices = Dropdown.get('operational_states').as_choices()
        self.fields['relationship_provider'].choices = get_node_type_tuples('Provider')

    name = forms.CharField(required=True)
    framing = forms.ChoiceField(widget=forms.widgets.Select)
    capacity = forms.ChoiceField(widget=forms.widgets.Select)
    wavelength = forms.IntegerField(required=False, help_text='Measured in GHz')
    operational_state = forms.ChoiceField(widget=forms.widgets.Select)
    description = description_field('optical path')
    enrs = JSONField(required=False, widget=JSONInput)
    relationship_provider = relationship_field('provider', True)
    relationship_depends_on = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)


class CsvForm(forms.Form):
    def __init__(self, csv_headers, *args, **kwargs):
        super(CsvForm, self).__init__(*args, **kwargs)
        self.csv_headers = csv_headers
        if not isinstance(csv_headers, str):
            placeholder = ", ".join(csv_headers)
        self.fields['csv_data'].widget.attrs['placeholder'] = placeholder
        help_text = u'CSV formatted data: "{}"'.format(placeholder)
        self.fields['csv_data'].help_text = help_text

    csv_data = forms.CharField(required=False,
                               widget=forms.Textarea(
                                   attrs={'rows': '5',
                                          'class': 'input-xxlarge'}))
    reviewed = forms.BooleanField(required=False)

    def csv_parse(self, func, validate=False):
        # Make sure cleaned_data is populated
        self.is_valid()
        lines = self.cleaned_data['csv_data'].splitlines()
        if six.PY3:
            # Py3 csv uses unicode
            reader = csv.DictReader(lines, fieldnames=self.csv_headers)
        else:
            # Py2.7 uses utf8 byte strings
            reader = csv.DictReader(self._utf8_enc(lines), fieldnames=self.csv_headers)
            reader = self._unicode(reader)
        return (func(line) for line in reader)

    def csv_parse_list(self, func, validate=False):
        return list(self.csv_parse(func, validate))

    def _utf8_enc(self, csv_lines):
        return (line.encode('utf-8') for line in csv_lines)

    def _unicode(self, dict_reader):
        for row in dict_reader:
            yield {key: (row[key] or '').decode('utf-8') for key in row.keys()}

    def form_to_csv(form, headers):
        cleaned = form.cleaned_data
        raw = form.data
        return u",".join([cleaned.get(h) or raw.get(h, '') for h in headers])


class NewOrganizationForm(forms.Form):
    account_id = forms.CharField(required=False)
    name = forms.CharField()
    description = description_field('organization')
    website = forms.CharField(required=False)
    customer_id = forms.CharField(required=False)
    type = forms.ChoiceField(widget=forms.widgets.Select, required=False)
    incident_management_info = forms.CharField(widget=forms.widgets.Textarea, required=False, label="Additional info for incident Mgmt")
    affiliation_customer = forms.BooleanField(required=False)
    affiliation_end_customer = forms.BooleanField(required=False)
    affiliation_provider = forms.BooleanField(required=False)
    affiliation_partner = forms.BooleanField(required=False)
    affiliation_host_user = forms.BooleanField(required=False)
    affiliation_site_owner = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(NewOrganizationForm, self).__init__(*args, **kwargs)
        self.fields['type'].choices = Dropdown.get('organization_types').as_choices()


class EditOrganizationForm(NewOrganizationForm):
    def __init__(self, *args, **kwargs):
        # set initial for contact combos
        initial = {} if 'initial' not in kwargs else kwargs['initial']

        if 'handle_id' in args[0]:
            organization_id = args[0]['handle_id']

            for field, roledict in DEFAULT_ROLES.items():
                role = Role.objects.get(slug=field)
                possible_contact = helpers.get_contact_for_orgrole(organization_id, role)

                if possible_contact:
                    args[0][field] = possible_contact.handle_id

        super(EditOrganizationForm, self).__init__(*args, **kwargs)
        self.fields['relationship_parent_of'].choices = get_node_type_tuples('Organization')
        self.fields['relationship_uses_a'].choices = get_node_type_tuples('Procedure')

        # contact choices
        if 'handle_id' in args[0]:
            organization_id = args[0]['handle_id']
            contact_choices = get_contacts_for_organization(organization_id)
            contact_type = NodeType.objects.get(slug='contact')
            contact_choices = [('', '')] + list(NodeHandle.objects.filter(node_type=contact_type).values_list('handle_id', 'node_name'))

            self.fields['abuse_contact'].choices = contact_choices
            self.fields['primary_contact'].choices = contact_choices
            self.fields['secondary_contact'].choices = contact_choices
            self.fields['it_technical_contact'].choices = contact_choices
            self.fields['it_security_contact'].choices = contact_choices
            self.fields['it_manager_contact'].choices = contact_choices

    relationship_parent_of = relationship_field('organization', True, [validate_contact])
    relationship_uses_a = relationship_field('procedure', True, [validate_procedure])

    abuse_contact = forms.ChoiceField(widget=forms.widgets.Select, required=False, label="Abuse", validators=[validate_contact])
    primary_contact = forms.ChoiceField(widget=forms.widgets.Select, required=False, label="Primary contact at incidents", validators=[validate_contact]) # Primary contact at incidents
    secondary_contact = forms.ChoiceField(widget=forms.widgets.Select, required=False, label="Secondary contact at incidents", validators=[validate_contact]) # Secondary contact at incidents
    it_technical_contact = forms.ChoiceField(widget=forms.widgets.Select, required=False, label="NOC Technical", validators=[validate_contact]) # NOC Technical
    it_security_contact = forms.ChoiceField(widget=forms.widgets.Select, required=False, label="NOC Security", validators=[validate_contact]) # NOC Security
    it_manager_contact = forms.ChoiceField(widget=forms.widgets.Select, required=False, label="NOC Manager", validators=[validate_contact]) # NOC Manager

    def clean(self):
        """
        Sets the default roles
        """
        cleaned_data = super(EditOrganizationForm, self).clean()
        for field, roledict in DEFAULT_ROLES.items():
            if field in self.data:
                value = self.data[field]
                if value:
                    try:
                        contact_handle_id = int(value)
                        cleaned_data[field] = contact_handle_id
                    except ValueError:
                        cleaned_data[field] = value

                    if field in self._errors:
                        del self._errors[field]


class NewContactForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(NewContactForm, self).__init__(*args, **kwargs)
        self.fields['contact_type'].choices = Dropdown.get('contact_type').as_choices()

    first_name = forms.CharField()
    last_name = forms.CharField()
    contact_type = forms.ChoiceField(widget=forms.widgets.Select)
    name = forms.CharField(required=False, widget=forms.widgets.HiddenInput)
    title = forms.CharField(required=False)
    pgp_fingerprint = forms.CharField(required=False, label='PGP fingerprint')
    notes = forms.CharField(widget=forms.widgets.Textarea, required=False, label="Notes")

    def clean(self, is_create=True):
        """
        Sets name from first and second name
        """
        cleaned_data = super(NewContactForm, self).clean()
        # Set name to a generated id if the service is not a manually named service.
        first_name = cleaned_data.get("first_name")
        last_name = cleaned_data.get("last_name")

        if six.PY2:
            first_name = first_name.encode('utf-8')
            last_name  = last_name.encode('utf-8')

        full_name = '{} {}'.format(first_name, last_name)
        node_type = NodeType.objects.get(type="Contact")
        cleaned_data['name'] = full_name

        return cleaned_data


class EditContactForm(NewContactForm):
    def __init__(self, *args, **kwargs):
        super(EditContactForm, self).__init__(*args, **kwargs)

        # init combos
        self.fields['relationship_works_for'].choices = get_node_type_tuples('Organization')
        self.fields['relationship_member_of'].choices = get_node_type_tuples('Group')
        self.fields['role'].choices = [('', '')] + list(Role.objects.all().values_list('handle_id', 'name'))

    relationship_works_for = relationship_field('organization', True, [validate_organization])
    relationship_member_of = relationship_field('group', True, [validate_group])
    role = forms.ChoiceField(required=False, widget=forms.widgets.Select)

    def clean(self):
        """
        Check empty role, set to employee
        """
        cleaned_data = super(EditContactForm, self).clean(False)
        role_id = cleaned_data.get("role")

        if not role_id:
            default_role = Role.objects.get(slug=DEFAULT_ROLE_KEY)
            cleaned_data['role'] = default_role.handle_id

        # clear organization and role selects
        if 'relationship_works_for' in self.data:
            self.data = self.data.copy()
            del self.data['relationship_works_for']

        if 'role' in self.data:
            self.data = self.data.copy()
            del self.data['role']

class NewProcedureForm(forms.Form):
    name = forms.CharField()
    description = description_field('procedure')


class EditProcedureForm(NewProcedureForm):
    pass


class NewGroupForm(forms.Form):
    name = forms.CharField()
    description = description_field('group')


class EditGroupForm(NewGroupForm):
    def __init__(self, *args, **kwargs):
        super(EditGroupForm, self).__init__(*args, **kwargs)
        self.fields['relationship_member_of'].choices = get_node_type_tuples('Contact')

    relationship_member_of = relationship_field('contact', True, [validate_contact])

    def clean(self):
        if 'relationship_member_of' in self.data:
            self.data = self.data.copy()
            del self.data['relationship_member_of']


class NewRoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ['name', 'description']


class EditRoleForm(forms.ModelForm):
    def save(self, commit=True):
        initial_name = self.initial['name']
        role = super(EditRoleForm, self).save(False)

        if self.has_changed():
            if 'name' in self.changed_data:
                nc.models.RoleRelationship.update_roles_withname(initial_name, role.name)
            role.save()

        return role

    class Meta:
        model = Role
        fields = ['name', 'description']


class PhoneForm(forms.Form):
    contact = forms.ChoiceField(widget=forms.widgets.Select, required=False, label="Contact", validators=[validate_contact])
    name = forms.CharField()
    type = forms.ChoiceField(widget=forms.widgets.Select)

    def __init__(self, *args, **kwargs):
        super(PhoneForm, self).__init__(*args, **kwargs)
        self.fields['contact'].choices = get_node_type_tuples('Contact')
        self.fields['type'].choices = phone_choices()


class EmailForm(forms.Form):
    contact = forms.ChoiceField(widget=forms.widgets.Select, required=False, label="Contact", validators=[validate_contact])
    name = forms.CharField()
    type = forms.ChoiceField(widget=forms.widgets.Select)

    def __init__(self, *args, **kwargs):
        super(EmailForm, self).__init__(*args, **kwargs)
        self.fields['contact'].choices = get_node_type_tuples('Contact')
        self.fields['type'].choices = email_choices()


class AddressForm(forms.Form):
    organization = forms.ChoiceField(widget=forms.widgets.Select, required=False, label="Organizations", validators=[validate_organization])
    name = forms.CharField()
    phone = forms.CharField(required=False)
    street = forms.CharField(required=False)
    postal_code = forms.CharField(required=False)
    postal_area = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)
        self.fields['organization'].choices = get_node_type_tuples('Organization')
