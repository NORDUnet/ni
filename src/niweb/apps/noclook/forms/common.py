from datetime import datetime
from django import forms
from django.forms.utils import ErrorDict, ErrorList, ValidationError
from django.forms.widgets import HiddenInput
from django.db import IntegrityError
import json
import csv
from apps.noclook.models import NodeHandle, UniqueIdGenerator, OpticalNodeType, ServiceType, NordunetUniqueId, Dropdown
from .. import unique_ids
import norduniclient as nc
from dynamic_preferences import global_preferences_registry


# We should move this kind of data to the SQL database.
def country_codes():
    codes = Dropdown.get('countries').as_values()
    return zip(codes, codes)


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


class DatePickerField(forms.DateField):
    def __init__(self, *args, **kwargs):
        super(DatePickerField, self).__init__(*args, **kwargs)
        self.widget = forms.TextInput(attrs={'data-provide': 'datepicker', 'data-date-format': 'yyyy-mm-dd'})


def description_field(name):
    return forms.CharField(required=False,
                           widget=forms.Textarea(attrs={'cols': '120', 'rows': '3'}),
                           help_text=u'Short description of the {}.'.format(name))


def relationship_field(name, select=False):
    labels = {
    }
    label = labels.get(name, name.title())
    if select:
        return forms.ChoiceField(required=False, label=label, widget=forms.widgets.Select)
    else:
        return forms.IntegerField(required=False, label=label, widget=forms.widgets.HiddenInput)


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

    name = forms.CharField()
    country_code = forms.ChoiceField(widget=forms.widgets.Select, required=False)
    country = forms.ChoiceField(widget=forms.widgets.Select, required=False)
    site_type = forms.ChoiceField(widget=forms.widgets.Select, required=False)
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
    relationship_responsible_for = relationship_field('responsible')

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

    name = forms.CharField()
    cable_type = forms.ChoiceField(widget=forms.widgets.Select)
    description = description_field('cable')
    relationship_provider = relationship_field('provider')


class EditCableForm(NewCableForm):
    relationship_end_a = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_end_b = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    relationship_provider = relationship_field('provider')


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
    relationship_location = relationship_field('location')


class EditOpticalNodeForm(OpticalNodeForm):
    relationship_ports = JSONField(required=False, widget=JSONInput)


class EditPeeringPartnerForm(forms.Form):
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
    rack_units = forms.IntegerField(required=False,
                                    label='Equipment height',
                                    help_text='Height in rack units (u).')
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
    operational_state = forms.ChoiceField(widget=forms.widgets.Select)
    relationship_location = relationship_field('location')
    relationship_ports = JSONField(required=False, widget=JSONInput)
    description = description_field('router')


class NewOdfForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(NewOdfForm, self).__init__(*args, **kwargs)
        # Set max number of ports to choose from
        max_num_of_ports = 48
        choices = [(x, x) for x in range(1, max_num_of_ports+1) if x]
        self.fields['max_number_of_ports'].choices = choices

    name = forms.CharField()
    max_number_of_ports = forms.ChoiceField(required=False, widget=forms.widgets.Select)


class BulkPortsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(BulkPortsForm, self).__init__(*args, **kwargs)
        self.fields['port_type'].choices = Dropdown.get('port_types').as_choices()

    no_ports = forms.BooleanField(required=False, help_text='Do not create any ports')
    bundled = forms.BooleanField(required=False, help_text='Bundle the ports e.g 1+2, 2+3 (half the ports)')
    port_type = forms.ChoiceField(required=False)
    prefix = forms.CharField(required=False, help_text='Port prefix e.g. ge-1/0')
    offset = forms.IntegerField(required=False, min_value=0, initial=1)
    num_ports = forms.IntegerField(required=False, min_value=0, initial=1)


class EditOdfForm(forms.Form):
    name = forms.CharField()
    max_number_of_ports = forms.IntegerField(required=False, help_text='Max number of ports.')
    rack_units = forms.IntegerField(required=False, help_text='Height in rack units (u).')
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
            if not name and service_type not in self.Meta.manually_named_services:
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

    name = forms.CharField(required=False)
    service_class = forms.CharField(required=False, widget=forms.widgets.HiddenInput)
    service_type = forms.ChoiceField(widget=forms.widgets.Select)
    project_end_date = forms.DateField(required=False)
    decommissioned_date = forms.DateField(required=False)
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
    relationship_provider = relationship_field('provider')
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
                self.add_error('name', e.message)
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
    relationship_depends_on = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)


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
                self._errors = ErrorDict()
                self._errors['name'] = ErrorList()
                self._errors['name'].append(e.message)
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
        reader = csv.DictReader(self._utf8_enc(lines),
                                fieldnames=self.csv_headers)
        return [func(line) for line in self._unicode(reader)]

    def _utf8_enc(self, csv_lines):
        return (line.encode('utf-8') for line in csv_lines)

    def _unicode(self, dict_reader):
        for row in dict_reader:
            yield {key: unicode(row[key] or '', 'utf-8') for key in row.keys()}

    def form_to_csv(form, headers):
        cleaned = form.cleaned_data
        raw = form.data
        return u",".join([cleaned.get(h) or raw.get(h, '') for h in headers])
