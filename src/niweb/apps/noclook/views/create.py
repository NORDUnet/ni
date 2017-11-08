# -*- coding: utf-8 -*-
"""
Created on 2012-11-07 4:43 PM

@author: lundberg
"""

from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import Http404
from django.shortcuts import render, redirect
from apps.noclook import forms
from apps.noclook.forms import common as common_forms
from apps.noclook.models import NodeHandle, Dropdown
from apps.noclook import helpers
from apps.noclook import unique_ids
from norduniclient.exceptions import UniqueNodeError, NoRelationshipPossible


TYPES = [
    ("customer", "Customer"),
    ("cable", "Cable"),
    ("end-user", "End User"),
    ("external-cable", "External Cable"),
    ("external-equipment", "External Equipment"),
    ("host", "Host"),
    ("optical-link", "Optical Link"),
    ("optical-path", "Optical Path"),
    ("service", "Service"),
    ("odf", "ODF"),
    ("optical-filter", "Optical Filter"),
    ("optical-multiplex-section", "Optical Multiplex Section"),
    ("optical-node", "Optical Node"),
    ("port", "Port"),
    ("provider", "Provider"),
    ("rack", "Rack"),
    ("site", "Site"),
    ("site-owner", "Site Owner"),
]
if helpers.app_enabled("apps.scan"):
    TYPES.append(("/scan/queue", "Host scan"))


# Create functions
@login_required
def new_node(request, slug=None, **kwargs):
    """
    Generic edit function that redirects calls to node type sensitive edit
    functions.
    """
    if not slug:
        types = sorted(TYPES, key=lambda x: x[1])
        return render(request, 'noclook/create/new_node.html', {"types": types})
    try:
        func = NEW_FUNC[slug]
    except KeyError:
        raise Http404
    return func(request, **kwargs)


@staff_member_required
def new_external_cable(request, **kwargs):
    if request.POST:
        form = common_forms.NewCableForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'cable', 'Physical')
            except UniqueNodeError:
                form = forms.NewCableForm(request.POST)
                form.add_error('name', 'A Cable with that name already exists.')
                return render(request, 'noclook/create/create_cable.html', {'form': form})
            helpers.form_update_node(request.user, nh.handle_id, form)
            return redirect(nh.get_absolute_url())
    else:
        name = kwargs.get('name', None)
        initial = {'name': name}
        form = common_forms.NewCableForm(initial=initial)
    return render(request, 'noclook/create/create_cable.html', {'form': form})


@staff_member_required
def new_customer(request, **kwargs):
    if request.POST:
        form = forms.NewCustomerForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'customer', 'Relation')
            except UniqueNodeError:
                form = forms.NewCustomerForm(request.POST)
                form.add_error('name', 'A Customer with that name already exists.')
                return render(request, 'noclook/create/create_customer.html', {'form': form})
            helpers.form_update_node(request.user, nh.handle_id, form)
            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewCustomerForm()
    return render(request, 'noclook/create/create_customer.html', {'form': form})


@staff_member_required
def new_end_user(request, **kwargs):

    if request.POST:
        form = forms.NewEndUserForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'end-user', 'Relation')
            except UniqueNodeError:
                form = forms.NewEndUserForm(request.POST)
                form.add_error('name', 'An End User with that name already exists.')
                return render(request, 'noclook/create/create_end_user.html', {'form': form})
            helpers.form_update_node(request.user, nh.handle_id, form)
            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewEndUserForm()
    return render(request, 'noclook/create/create_end_user.html', {'form': form})


@staff_member_required
def new_external_equipment(request, **kwargs):
    if request.POST:
        form = forms.NewExternalEquipmentForm(request.POST)
        if form.is_valid():
            nh = helpers.form_to_generic_node_handle(request, form, 'external-equipment', 'Physical')
            helpers.form_update_node(request.user, nh.handle_id, form)
            data = form.cleaned_data
            node = nh.get_node()
            if data['relationship_location']:
                location = NodeHandle.objects.get(pk=data['relationship_location'])
                helpers.set_location(request.user, node, location.handle_id)
            if data['relationship_owner']:
                owner = NodeHandle.objects.get(pk=data['relationship_owner'])
                helpers.set_owner(request.user, node, owner.handle_id)
            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewExternalEquipmentForm()
    return render(request, 'noclook/create/create_external_equipment.html', {'form': form})


@staff_member_required
def new_cable(request, **kwargs):
    cable_types = u', '.join([u'"{}"'.format(val) for val in Dropdown.get('cable_types').as_values()])
    if request.POST:
        form = forms.NewCableForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'cable', 'Physical')
            except UniqueNodeError:
                form = forms.NewCableForm(request.POST)
                form.add_error('name', 'A Cable with that name already exists.')
                return render(request, 'noclook/create/create_cable.html', {'form': form})
            helpers.form_update_node(request.user, nh.handle_id, form)
            if form.cleaned_data['relationship_provider']:
                node = nh.get_node()
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return redirect(nh.get_absolute_url())
    else:
        name = kwargs.get('name', None)
        initial = {'name': name}
        form = forms.NewCableForm(initial=initial)
    csv_form = forms.CsvForm(['name, cable_type, description'], request.POST or None)
    return render(request, 'noclook/create/create_cable.html', {'form': form, 'csv_form': csv_form, 'cable_types': cable_types})


def _csv_to_cable_form(data):
    data['cable_type'] = data.get('cable_type', '').strip().title()
    if data.get('name'):
        data['name'] = data['name'].strip()
    return forms.NewCableForm(data)


def _form_to_csv(form, headers):
    cleaned = form.cleaned_data
    raw = form.data
    return u",".join([cleaned.get(h) or raw.get(h, '') for h in headers])


def _forms_to_csv(forms, headers):
    csv_lines = [_form_to_csv(f, headers) for f in forms]
    return u'\n'.join(csv_lines)


def _create_cables(request, cables):
    error_cables = []
    for cable in cables:
        try:
            nh = helpers.form_to_unique_node_handle(request,
                                                    cable,
                                                    'cable',
                                                    'Physical')
        except UniqueNodeError:
            cable.add_error('name', 'A cable with this name already exists')
            error_cables.append(cable)
            continue
        helpers.form_update_node(request.user, nh.handle_id, cable)
    return error_cables


@staff_member_required
def new_cable_csv(request):
    csv_headers = ['name', 'cable_type', 'description']
    cable_types = u', '.join([u'"{}"'.format(val) for val in Dropdown.get('cable_types').as_values()])
    form = forms.CsvForm(csv_headers, request.POST or None)

    form.is_valid()
    csv_data = form.cleaned_data['csv_data']
    show_view = {}
    errors = False

    if csv_data:
        # check errors
        cables = form.csv_parse(_csv_to_cable_form)
        for cable in cables:
            if not cable.is_valid():
                errors = True

        if not errors and form.cleaned_data['reviewed']:
            # Time to save data!
            error_cables = _create_cables(request, cables)
            if error_cables:
                show_view = {'cables': error_cables}
            else:
                msg = 'Successfully added {} cables'.format(len(cables))
                messages.success(request, msg)
        else:
            show_view = {'reviewed': True, 'cables': cables}

    if show_view:
        new_csv = _forms_to_csv(show_view.get('cables'), csv_headers)
        form = forms.CsvForm(csv_headers,
                             {'csv_data': new_csv,
                              'reviewed': show_view.get('reviewed', False)})
        return render(request, 'noclook/create/create_cable_csv.html',
                      {'form': form,
                       'cables': show_view.get('cables'),
                       'cable_types': cable_types})
    else:
        # TODO: stop using hardcoded urls :(
        return redirect('/cable/')


@staff_member_required
def new_host(request):
    form = forms.NewHostForm(request.POST or None)
    user = request.user

    if request.POST:
        if form.is_valid():
            data = form.cleaned_data
            if data['relationship_owner'] or data['relationship_location']:
                meta_type = 'Physical'
            else:
                meta_type = 'Logical'

            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'host', meta_type)
            except UniqueNodeError:
                form.add_error('name', 'A Host with that name already exists.')
                return render(request,
                              'noclook/create/create_host.html',
                              {'form': form})
            helpers.form_update_node(user, nh.handle_id, form)
            node = nh.get_node()
            if data['relationship_owner']:
                owner = NodeHandle.objects.get(pk=data['relationship_owner'])
                helpers.set_owner(user, node, owner.handle_id)
            if data['relationship_location']:
                location = NodeHandle.objects.get(pk=data['relationship_location'])
                helpers.set_location(user, node, location.handle_id)
            return redirect(nh.get_absolute_url())
    return render(request,
                  'noclook/create/create_host.html',
                  {'form': form})


@staff_member_required
def new_optical_link(request, **kwargs):
    if request.POST:
        form = forms.NewOpticalLinkForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'optical-link', 'Logical')
            except UniqueNodeError:
                form.add_error('name', 'An Optical Link with that name already exists.')
                return render(request, 'noclook/create/create_optical_link.html', {'form': form})
            helpers.form_update_node(request.user, nh.handle_id, form)
            if form.cleaned_data['relationship_provider']:
                node = nh.get_node()
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewOpticalLinkForm()
    return render(request, 'noclook/create/create_optical_link.html', {'form': form})


@staff_member_required
def new_optical_path(request, **kwargs):
    if request.POST:
        form = forms.NewOpticalPathForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'optical-path', 'Logical')
            except UniqueNodeError:
                form = forms.NewOpticalPathForm(request.POST)
                form.add_error('name', 'An Optical Path with that name already exists.')
                return render(request, 'noclook/create/create_optical_path.html', {'form': form})
            helpers.form_update_node(request.user, nh.handle_id, form)
            if form.cleaned_data['relationship_provider']:
                node = nh.get_node()
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewOpticalPathForm()
    return render(request, 'noclook/create/create_optical_path.html', {'form': form})


@staff_member_required
def new_service(request, **kwargs):
    if request.POST:
        form = forms.NewServiceForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'service', 'Logical')
            except UniqueNodeError:
                form = forms.NewServiceForm(request.POST)
                form.add_error('name', 'A Service with that name already exists.')
                return render(request, 'noclook/create/create_service.html', {'form': form})
            helpers.form_update_node(request.user, nh.handle_id, form)
            if form.cleaned_data['relationship_provider']:
                node = nh.get_node()
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewServiceForm()
    return render(request, 'noclook/create/create_service.html', {'form': form})


@staff_member_required
def new_odf(request, **kwargs):
    if request.POST:
        form = forms.NewOdfForm(request.POST)
        ports_form = forms.BulkPortsForm(request.POST)
        if form.is_valid() and ports_form.is_valid():
            nh = helpers.form_to_generic_node_handle(request, form, 'odf', 'Physical')
            helpers.form_update_node(request.user, nh.handle_id, form)
            if not ports_form.cleaned_data['no_ports']:
                data = ports_form.cleaned_data
                helpers.bulk_create_ports(nh.get_node(), request.user, **data)

            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewOdfForm()
        ports_form = forms.BulkPortsForm({'port_type': 'LC', 'offset': 1, 'num_ports': '0'})
    return render(request, 'noclook/create/create_odf.html', {'form': form, 'ports_form': ports_form})


@staff_member_required
def new_optical_filter(request, **kwargs):
    form = forms.NewOpticalFilter(request.POST or None)
    ports_form = forms.BulkPortsForm(request.POST or None)

    if request.POST:
        if form.is_valid() and ports_form.is_valid():
            nh = helpers.form_to_generic_node_handle(request, form, 'optical-filter', 'Physical')
            helpers.form_update_node(request.user, nh.handle_id, form)
            if not ports_form.cleaned_data['no_ports']:
                data = ports_form.cleaned_data
                helpers.bulk_create_ports(nh.get_node(), request.user, **data)

            return redirect(nh.get_absolute_url())

    return render(request, 'noclook/create/create_optical_filter.html', {'form': form, 'ports_form': ports_form})


@staff_member_required
def new_optical_multiplex_section(request, **kwargs):
    if request.POST:
        form = forms.NewOpticalMultiplexSectionForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'optical-multiplex-section', 'Logical')
            except UniqueNodeError:
                form = forms.NewOpticalMultiplexSectionForm(request.POST)
                form.add_error('name', 'An Optical Multiplex Section with that name already exists.')
                return render(request,
                              'noclook/create/create_optical_multiplex_section.html',
                              {'form': form})
            helpers.form_update_node(request.user, nh.handle_id, form)
            if form.cleaned_data['relationship_provider']:
                node = nh.get_node()
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewOpticalMultiplexSectionForm()
    return render(request, 'noclook/create/create_optical_multiplex_section.html', {'form': form})


@staff_member_required
def new_port(request, **kwargs):
    if request.POST:
        form = forms.NewPortForm(request.POST)
        if form.is_valid():
            nh = helpers.form_to_generic_node_handle(request, form, 'port', 'Physical')
            helpers.form_update_node(request.user, nh.handle_id, form)
            if kwargs.get('parent_id', None) or form.cleaned_data['relationship_parent']:
                parent_id = kwargs.get('parent_id', None)
                if not parent_id:
                    parent_id = form.cleaned_data['relationship_parent']
                try:
                    parent_nh = NodeHandle.objects.get(pk=parent_id)
                    helpers.set_has(request.user, parent_nh.get_node(), nh.handle_id)
                except NoRelationshipPossible:
                    nh.delete()
                    form = forms.NewPortForm(request.POST)
                    form.add_error('parent', 'Parent type can not have ports.')
                    return render(request, 'noclook/create/create_port.html', {'form': form})
            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewPortForm()
    return render(request,
                  'noclook/create/create_port.html',
                  {'form': form})


@staff_member_required
def new_provider(request, **kwargs):
    if request.POST:
        form = forms.NewProviderForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'provider', 'Relation')
            except UniqueNodeError:
                form = forms.NewProviderForm(request.POST)
                form.add_error('name', 'A Provider with that name already exists.')
                return render(request, 'noclook/create/create_provider.html', {'form': form})
            helpers.form_update_node(request.user, nh.handle_id, form)
            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewProviderForm()
    return render(request, 'noclook/create/create_provider.html', {'form': form})


@staff_member_required
def new_rack(request, **kwargs):
    if request.POST:
        form = forms.NewRackForm(request.POST)
        if form.is_valid():
            nh = helpers.form_to_generic_node_handle(request, form, 'rack', 'Location')
            helpers.form_update_node(request.user, nh.handle_id, form)
            if form.cleaned_data['relationship_location']:
                parent_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                helpers.set_has(request.user, parent_nh.get_node(), nh.handle_id)
            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewRackForm()
    return render(request, 'noclook/create/create_rack.html', {'form': form})


@staff_member_required
def new_site(request, **kwargs):
    if request.POST:
        form = forms.NewSiteForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'site', 'Location')
            except UniqueNodeError:
                form.add_error('name', 'A Site with that name already exists.')
                return render(request, 'noclook/create/create_site.html', {'form': form})
            helpers.form_update_node(request.user, nh.handle_id, form)
            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewSiteForm()
    return render(request, 'noclook/create/create_site.html', {'form': form})


@staff_member_required
def new_site_owner(request, **kwargs):
    if request.POST:
        form = forms.NewSiteOwnerForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'site-owner', 'Relation')
            except UniqueNodeError:
                form = forms.NewSiteOwnerForm(request.POST)
                form.add_error('name', 'A Site Owner with that name already exists.')
                return render(request, 'noclook/create/create_site_owner.html', {'form': form})
            helpers.form_update_node(request.user, nh.handle_id, form)
            return redirect(nh.get_absolute_url())
    else:
        form = forms.NewSiteOwnerForm()
    return render(request, 'noclook/create/create_site_owner.html', {'form': form})


@staff_member_required
def new_optical_node(request, slug=None):
    form = forms.OpticalNodeForm(request.POST or None)
    bulk_ports = forms.BulkPortsForm(request.POST or None)

    if request.POST and form.is_valid() and bulk_ports.is_valid():
        try:
            name = form.cleaned_data['name']
            nh = helpers.create_unique_node_handle(request.user,
                                                name,
                                                'optical-node',
                                                'Physical')
            helpers.form_update_node(request.user, nh.handle_id, form)
            node = nh.get_node()
            user = request.user
            if form.cleaned_data['relationship_location']:
                location = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                helpers.set_location(user, node, location.handle_id)

            # create ports if needed
            if not bulk_ports.cleaned_data['no_ports']:
                data = bulk_ports.cleaned_data
                helpers.bulk_create_ports(nh.get_node(), request.user, **data)
            return redirect(nh.get_absolute_url())
        except UniqueNodeError:
            form.add_error('name', 'An Optical Node with that name already exists.')
    return render(request, 'noclook/create/create_optical_node.html', {'form': form, 'bulk_ports': bulk_ports})


# Reserve Ids
@staff_member_required
def reserve_id_sequence(request, slug=None):
    if not slug:
        return render(request, 'noclook/edit/reserve_id.html', {})
    if request.POST:
        form = forms.ReserveIdForm(request.POST)
        if form.is_valid():
            unique_id_generator, unique_id_collection = unique_ids.unique_id_map(slug)
            if not unique_id_generator or not unique_id_collection:
                raise Http404
            reserved_list = unique_ids.reserve_id_sequence(
                form.cleaned_data['amount'],
                unique_id_generator,
                unique_id_collection,
                form.cleaned_data['reserve_message'],
                request.user,
                form.cleaned_data['site']
            )
            return render(request, 'noclook/edit/reserve_id.html', {'reserved_list': reserved_list, 'slug': slug})
        else:
            return render(request, 'noclook/edit/reserve_id.html', {'form': form, 'slug': slug})
    else:
        form = forms.ReserveIdForm()
        return render(request, 'noclook/edit/reserve_id.html', {'form': form, 'slug': slug})


NEW_FUNC = {
    'cable': new_cable,
    'cable_csv': new_cable_csv,
    'customer': new_customer,
    'end-user': new_end_user,
    'external-equipment': new_external_equipment,
    'external-cable': new_external_cable,
    'host': new_host,
    'odf': new_odf,
    'optical-filter': new_optical_filter,
    'optical-link': new_optical_link,
    'optical-multiplex-section': new_optical_multiplex_section,
    'optical-path': new_optical_path,
    'port': new_port,
    'provider': new_provider,
    'rack': new_rack,
    'service': new_service,
    'site': new_site,
    'site-owner': new_site_owner,
    'optical-node': new_optical_node,
}
