# -*- coding: utf-8 -*-
"""
Created on 2012-11-07 4:43 PM

@author: lundberg
"""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.forms.util import ErrorDict, ErrorList
from apps.noclook import forms
from apps.noclook.models import NodeHandle
from apps.noclook import helpers
from apps.noclook import unique_ids
from norduniclient.exceptions import UniqueNodeError, NoRelationshipPossible
import norduniclient as nc


# Helper functions
def get_provider_id(provider_name):
    """
    Get a node id to be able to provide a forms initial with a default provider.
    :provider_name String Provider name
    :return String Provider node id or empty string
    """
    provider = nc.get_nodes_by_value(nc.neo4jdb, provider_name, 'name', 'Provider')
    try:
        provider_id = str(provider.next().get('handle_id', ''))
    except StopIteration:
        provider_id = ''
    provider.close()
    return provider_id


# Create functions
@login_required
def new_node(request, slug=None, **kwargs):
    """
    Generic edit function that redirects calls to node type sensitive edit
    functions.
    """
    if not request.user.is_staff:
        raise Http404
    if not slug:
        return render_to_response('noclook/create/new_node.html', {}, context_instance=RequestContext(request))
    try:
        func = NEW_FUNC[slug]
    except KeyError:
        raise Http404
    return func(request, **kwargs)


@login_required
def new_cable(request, **kwargs):
    if request.POST:
        form = forms.NewCableForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'cable', 'Physical')
            except UniqueNodeError:
                form = forms.NewCableForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('A Cable with that name already exists.')
                return render_to_response('noclook/create/create_cable.html', {'form': form},
                                          context_instance=RequestContext(request))
            node = nh.get_node()
            keys = ['cable_type']
            helpers.form_update_node(request.user, node.handle_id, form, keys)
            return HttpResponseRedirect(nh.get_absolute_url())
        else:
            name = kwargs.get('name', None)
        if name:
            initital = {'name': name}
            form = forms.NewCableForm(initial=initital)
    else:
        form = forms.NewCableForm()
    return render_to_response('noclook/create/create_cable.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_customer(request, **kwargs):
    if request.POST:
        form = forms.NewCustomerForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'customer', 'Relation')
            except UniqueNodeError:
                form = forms.NewCustomerForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('A Customer with that name already exists.')
                return render_to_response('noclook/create/create_customer.html', {'form': form},
                                          context_instance=RequestContext(request))
            node = nh.get_node()
            keys = ['url']
            helpers.form_update_node(request.user, node.handle_id, form, keys)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewCustomerForm()
    return render_to_response('noclook/create/create_customer.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_end_user(request, **kwargs):
    if request.POST:
        form = forms.NewEndUserForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'end-user', 'Relation')
            except UniqueNodeError:
                form = forms.NewEndUserForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('An End User with that name already exists.')
                return render_to_response('noclook/create/create_end_user.html', {'form': form},
                    context_instance=RequestContext(request))
            node = nh.get_node()
            keys = ['url']
            helpers.form_update_node(request.user, node.handle_id, form, keys)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewEndUserForm()
    return render_to_response('noclook/create/create_end_user.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_external_equipment(request, **kwargs):
    if request.POST:
        form = forms.NewExternalEquipmentForm(request.POST)
        if form.is_valid():
            nh = helpers.form_to_generic_node_handle(request, form, 'external-equipment', 'Physical')
            node = nh.get_node()
            helpers.form_update_node(request.user, node.handle_id, form)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewExternalEquipmentForm()
    return render_to_response('noclook/create/create_external_equipment.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_nordunet_cable(request, **kwargs):
    if request.POST:
        form = forms.NewNordunetCableForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'cable', 'Physical')
            except UniqueNodeError:
                form = forms.NewNordunetCableForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('A Cable with that name already exists.')
                return render_to_response('noclook/create/create_cable.html', {'form': form},
                                          context_instance=RequestContext(request))
            node = nh.get_node()
            keys = ['cable_type']
            helpers.form_update_node(request.user, node.handle_id, form, keys)
            if form.cleaned_data['relationship_provider']:
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            # Provider
            if form.cleaned_data['relationship_provider']:
                provider_id = form.cleaned_data['relationship_provider']
                helpers.set_provider(request.user, node, provider_id)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        name = kwargs.get('name', None)
        provider_id = get_provider_id('NORDUnet')
        initial = {'relationship_provider': provider_id}
        if name:
            initial['name'] = name
        form = forms.NewNordunetCableForm(initial=initial)
    return render_to_response('noclook/create/create_cable.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_nordunet_optical_link(request, **kwargs):
    if request.POST:
        form = forms.NewNordunetOpticalLinkForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'optical-link', 'Logical')
            except UniqueNodeError:
                form = forms.NewNordunetOpticalLinkForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('An Optical Link with that name already exists.')
                return render_to_response('noclook/create/create_nordunet_optical_link.html', {'form': form},
                                          context_instance=RequestContext(request))
            node = nh.get_node()
            keys = ['description', 'link_type', 'operational_state', 'interface_type']
            helpers.form_update_node(request.user, node.handle_id, form, keys)
            if form.cleaned_data['relationship_provider']:
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        provider_id = get_provider_id('NORDUnet')
        initial = {'relationship_provider': provider_id, 'interface_type': 'WDM'}
        form = forms.NewNordunetOpticalLinkForm(initial=initial)
    return render_to_response('noclook/create/create_nordunet_optical_link.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_nordunet_optical_path(request, **kwargs):
    if request.POST:
        form = forms.NewNordunetOpticalPathForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'optical-path', 'Logical')
            except UniqueNodeError:
                form = forms.NewNordunetOpticalPathForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('An Optical Path with that name already exists.')
                return render_to_response('noclook/create/create_nordunet_optical_path.html', {'form': form},
                                          context_instance=RequestContext(request))
            node = nh.get_node()
            keys = ['description', 'framing', 'capacity', 'operational_state']
            helpers.form_update_node(request.user, node.handle_id, form, keys)
            if form.cleaned_data['relationship_provider']:
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        provider_id = get_provider_id('NORDUnet')
        form = forms.NewNordunetOpticalPathForm(initial={'relationship_provider': provider_id})
    return render_to_response('noclook/create/create_nordunet_optical_path.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_nordunet_service(request, **kwargs):
    if request.POST:
        form = forms.NewNordunetServiceForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'service', 'Logical')
            except UniqueNodeError:
                form = forms.NewNordunetServiceForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('A Service with that name already exists.')
                return render_to_response('noclook/create/create_nordunet_service.html', {'form': form},
                                          context_instance=RequestContext(request))
            node = nh.get_node()
            keys = ['description', 'service_class', 'service_type', 'operational_state', 'project_end_date']
            helpers.form_update_node(request.user, node.handle_id, form, keys)
            if form.cleaned_data['relationship_provider']:
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        provider_id = get_provider_id('NORDUnet')
        form = forms.NewNordunetServiceForm(initial={'relationship_provider': provider_id})
    return render_to_response('noclook/create/create_nordunet_service.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_odf(request, **kwargs):
    if request.POST:
        form = forms.NewOdfForm(request.POST)
        if form.is_valid():
            nh = helpers.form_to_generic_node_handle(request, form, 'odf', 'Physical')
            node = nh.get_node()
            helpers.form_update_node(request.user, node.handle_id, form)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewOdfForm()
    return render_to_response('noclook/create/create_odf.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_optical_multiplex_section(request, **kwargs):
    if request.POST:
        form = forms.NewOpticalMultiplexSectionForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'optical-multiplex-section', 'Logical')
            except UniqueNodeError:
                form = forms.NewOpticalMultiplexSectionForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('An Optical Multiplex Section with that name already exists.')
                return render_to_response('noclook/create/create_optical_multiplex_section.html',
                                          {'form': form}, context_instance=RequestContext(request))
            node = nh.get_node()
            keys = ['name', 'description', 'operational_state']
            helpers.form_update_node(request.user, node.handle_id, form, keys)
            if form.cleaned_data['relationship_provider']:
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        provider_id = get_provider_id('NORDUnet')
        form = forms.NewOpticalMultiplexSectionForm(initial={'relationship_provider': provider_id})
    return render_to_response('noclook/create/create_optical_multiplex_section.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_port(request, **kwargs):
    if request.POST:
        form = forms.NewPortForm(request.POST)
        if form.is_valid():
            nh = helpers.form_to_generic_node_handle(request, form, 'port', 'Physical')
            node = nh.get_node()
            keys = ['port_type']
            helpers.form_update_node(request.user, node.handle_id, form, keys)
            if kwargs.get('parent_id', None):
                try:
                    parent_nh = NodeHandle.objects.get(pk=kwargs['parent_id'])
                    helpers.set_has(request.user, parent_nh.get_node(), nh.handle_id)
                except NoRelationshipPossible:
                    nh.delete()
                    form = forms.NewSiteForm(request.POST)
                    form._errors = ErrorDict()
                    form._errors['parent'] = ErrorList()
                    form._errors['parent'].append('Parent type can not have ports.')
                    return render_to_response('noclook/create/create_port.html', {'form': form},
                                              context_instance=RequestContext(request))
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewPortForm()
    return render_to_response('noclook/create/create_port.html', {'form': form},
                                  context_instance=RequestContext(request))


@login_required
def new_provider(request, **kwargs):
    if request.POST:
        form = forms.NewProviderForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'provider', 'Relation')
            except UniqueNodeError:
                form = forms.NewProviderForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('A Provider with that name already exists.')
                return render_to_response('noclook/create/create_provider.html', {'form': form},
                    context_instance=RequestContext(request))
            node = nh.get_node()
            keys = ['url']
            helpers.form_update_node(request.user, node.handle_id, form, keys)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewProviderForm()
    return render_to_response('noclook/create/create_provider.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_rack(request, **kwargs):
    if request.POST:
        form = forms.NewRackForm(request.POST)
        if form.is_valid():
            nh = helpers.form_to_generic_node_handle(request, form, 'rack', 'Location')
            node = nh.get_node()
            helpers.form_update_node(request.user, node.handle_id, form)
            if form.cleaned_data['relationship_location']:
                parent_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                helpers.set_has(request.user, parent_nh.get_node(), nh.handle_id)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewRackForm()
    return render_to_response('noclook/create/create_rack.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_site(request, **kwargs):
    if request.POST:
        form = forms.NewSiteForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'site', 'Location')
            except UniqueNodeError:
                form = forms.NewSiteForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('A Site with that name already exists.')
                return render_to_response('noclook/create/create_site.html', {'form': form},
                    context_instance=RequestContext(request))
            node = nh.get_node()
            keys = ['country', 'country_code', 'address', 'postarea', 'postcode']
            helpers.form_update_node(request.user, node.handle_id, form, keys)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewSiteForm()
    return render_to_response('noclook/create/create_site.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_site_owner(request, **kwargs):
    if request.POST:
        form = forms.NewSiteOwnerForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'site-owner', 'Relation')
            except UniqueNodeError:
                form = forms.NewSiteOwnerForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('A Site Owner with that name already exists.')
                return render_to_response('noclook/create/create_site_owner.html', {'form': form},
                    context_instance=RequestContext(request))
            node = nh.get_node()
            keys = ['url']
            helpers.form_update_node(request.user, node.handle_id, form, keys)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewSiteOwnerForm()
    return render_to_response('noclook/create/create_site_owner.html', {'form': form},
                              context_instance=RequestContext(request))


# Reserve Ids
@login_required
def reserve_id_sequence(request, slug=None):
    if not slug:
        return render_to_response('noclook/edit/reserve_id.html', {}, context_instance=RequestContext(request))
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
                request.user
            )
            return render_to_response('noclook/edit/reserve_id.html', {'reserved_list': reserved_list, 'slug': slug},
                                      context_instance=RequestContext(request))
    else:
        form = forms.ReserveIdForm()
        return render_to_response('noclook/edit/reserve_id.html', {'form': form, 'slug': slug},
                                  context_instance=RequestContext(request))

NEW_FUNC = {
    'cable': new_cable,
    'customer': new_customer,
    'end-user': new_end_user,
    'external-equipment': new_external_equipment,
    'nordunet-cable': new_nordunet_cable,
    'nordunet-optical-link': new_nordunet_optical_link,
    'nordunet-optical-path': new_nordunet_optical_path,
    'nordunet-service': new_nordunet_service,
    'odf': new_odf,
    'optical-multiplex-section': new_optical_multiplex_section,
    'port': new_port,
    'provider': new_provider,
    'rack': new_rack,
    'site': new_site,
    'site-owner': new_site_owner,
}
