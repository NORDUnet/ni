# -*- coding: utf-8 -*-
"""
Created on 2012-11-07 4:43 PM

@author: lundberg
"""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.forms.utils import ErrorDict, ErrorList
from apps.noclook import forms
from apps.noclook.forms import common as common_forms
from apps.noclook.models import NodeHandle
from apps.noclook import helpers
from apps.noclook import unique_ids
from norduniclient.exceptions import UniqueNodeError, NoRelationshipPossible


# Create functions
@login_required
def new_node(request, slug=None, **kwargs):
    """
    Generic edit function that redirects calls to node type sensitive edit
    functions.
    """
    if not slug:
        return render_to_response('noclook/create/new_node.html', {}, context_instance=RequestContext(request))
    try:
        func = NEW_FUNC[slug]
    except KeyError:
        raise Http404
    return func(request, **kwargs)


@login_required
def new_external_cable(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.POST:
        form = common_forms.NewCableForm(request.POST)
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
            helpers.form_update_node(request.user, nh.handle_id, form)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        name = kwargs.get('name', None)
        initial = {'name': name}
        form = common_forms.NewCableForm(initial=initial)
    return render_to_response('noclook/create/create_cable.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_customer(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

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
            helpers.form_update_node(request.user, nh.handle_id, form)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewCustomerForm()
    return render_to_response('noclook/create/create_customer.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_end_user(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

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
            helpers.form_update_node(request.user, nh.handle_id, form)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewEndUserForm()
    return render_to_response('noclook/create/create_end_user.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_external_equipment(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.POST:
        form = forms.NewExternalEquipmentForm(request.POST)
        if form.is_valid():
            nh = helpers.form_to_generic_node_handle(request, form, 'external-equipment', 'Physical')
            helpers.form_update_node(request.user, nh.handle_id, form)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewExternalEquipmentForm()
    return render_to_response('noclook/create/create_external_equipment.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_cable(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

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
            helpers.form_update_node(request.user, nh.handle_id, form)
            if form.cleaned_data['relationship_provider']:
                node = nh.get_node()
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        name = kwargs.get('name', None)
        initial = {'name': name}
        form = forms.NewCableForm(initial=initial)
    return render_to_response('noclook/create/create_cable.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_optical_link(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.POST:
        form = forms.NewOpticalLinkForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'optical-link', 'Logical')
            except UniqueNodeError:
                form = forms.NewOpticalLinkForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('An Optical Link with that name already exists.')
                return render_to_response('noclook/create/create_link.html', {'form': form},
                                          context_instance=RequestContext(request))
            helpers.form_update_node(request.user, nh.handle_id, form)
            if form.cleaned_data['relationship_provider']:
                node = nh.get_node()
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewOpticalLinkForm()
    return render_to_response('noclook/create/create_optical_link.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_optical_path(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.POST:
        form = forms.NewOpticalPathForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'optical-path', 'Logical')
            except UniqueNodeError:
                form = forms.NewOpticalPathForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('An Optical Path with that name already exists.')
                return render_to_response('noclook/create/create_optical_path.html', {'form': form},
                                          context_instance=RequestContext(request))
            helpers.form_update_node(request.user, nh.handle_id, form)
            if form.cleaned_data['relationship_provider']:
                node = nh.get_node()
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewOpticalPathForm()
    return render_to_response('noclook/create/create_optical_path.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_service(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.POST:
        form = forms.NewServiceForm(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form, 'service', 'Logical')
            except UniqueNodeError:
                form = forms.NewServiceForm(request.POST)
                form._errors = ErrorDict()
                form._errors['name'] = ErrorList()
                form._errors['name'].append('A Service with that name already exists.')
                return render_to_response('noclook/create/create_service.html', {'form': form},
                                          context_instance=RequestContext(request))
            helpers.form_update_node(request.user, nh.handle_id, form)
            if form.cleaned_data['relationship_provider']:
                node = nh.get_node()
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewServiceForm()
    return render_to_response('noclook/create/create_service.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_odf(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.POST:
        form = forms.NewOdfForm(request.POST)
        if form.is_valid():
            nh = helpers.form_to_generic_node_handle(request, form, 'odf', 'Physical')
            helpers.form_update_node(request.user, nh.handle_id, form)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewOdfForm()
    return render_to_response('noclook/create/create_odf.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_optical_multiplex_section(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

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
            helpers.form_update_node(request.user, nh.handle_id, form)
            if form.cleaned_data['relationship_provider']:
                node = nh.get_node()
                provider_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, node, provider_nh.handle_id)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewOpticalMultiplexSectionForm()
    return render_to_response('noclook/create/create_optical_multiplex_section.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_port(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

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
    if not request.user.is_staff:
        return HttpResponseForbidden()

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
            helpers.form_update_node(request.user, nh.handle_id, form)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewProviderForm()
    return render_to_response('noclook/create/create_provider.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_rack(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.POST:
        form = forms.NewRackForm(request.POST)
        if form.is_valid():
            nh = helpers.form_to_generic_node_handle(request, form, 'rack', 'Location')
            helpers.form_update_node(request.user, nh.handle_id, form)
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
    if not request.user.is_staff:
        return HttpResponseForbidden()

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
            helpers.form_update_node(request.user, nh.handle_id, form)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewSiteForm()
    return render_to_response('noclook/create/create_site.html', {'form': form},
                              context_instance=RequestContext(request))


@login_required
def new_site_owner(request, **kwargs):
    if not request.user.is_staff:
        return HttpResponseForbidden()

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
            helpers.form_update_node(request.user, nh.handle_id, form)
            return HttpResponseRedirect(nh.get_absolute_url())
    else:
        form = forms.NewSiteOwnerForm()
    return render_to_response('noclook/create/create_site_owner.html', {'form': form},
                              context_instance=RequestContext(request))


# Reserve Ids
@login_required
def reserve_id_sequence(request, slug=None):
    if not request.user.is_staff:
        return HttpResponseForbidden()

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
                request.user,
                form.cleaned_data['site'] 
            )
            return render_to_response('noclook/edit/reserve_id.html', {'reserved_list': reserved_list, 'slug': slug},
                                      context_instance=RequestContext(request))
        else:
            return render_to_response('noclook/edit/reserve_id.html', {'form': form, 'slug': slug},
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
    'external-cable': new_external_cable,
    'optical-path': new_optical_path,
    'service': new_service,
    'odf': new_odf,
    'optical-multiplex-section': new_optical_multiplex_section,
    'port': new_port,
    'provider': new_provider,
    'rack': new_rack,
    'site': new_site,
    'site-owner': new_site_owner,
}
