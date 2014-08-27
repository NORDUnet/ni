# -*- coding: utf-8 -*-
"""
Created on Wed Dec 14 14:00:03 2011

@author: lundberg

Node manipulation views.
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
import json
from apps.noclook.models import NodeHandle
from apps.noclook import forms
from apps.noclook import activitylog
import apps.noclook.helpers as h
import norduniclient as nc


# Helper functions
@login_required
def delete_node(request, slug, handle_id):
    """
    Removes the node and all its relationships.
    """
    nh, node = h.get_nh_node(handle_id)
    h.delete_node(request.user, node)
    return HttpResponseRedirect('/%s' % slug)


@login_required
def delete_relationship(request, slug, handle_id, rel_id):
    """
    Removes the relationship if the node has a relationship matching the
    supplied id.
    """
    nh, node = h.get_nh_node(handle_id)
    relationship = nc.get_relationship_model(nc.neo4jdb, rel_id)
    if node == relationship.start or node == relationship.end:
        activitylog.delete_relationship(request.user, relationship)
        relationship.delete()
        return HttpResponseRedirect('/%s/%d/edit' % (slug, nh.handle_id))
    raise Http404


# Form data returns
@login_required
def get_node_type(request, slug):
    """
    Compiles a list of alla nodes of that node type and returns a list of
    node name, node id tuples.
    """
    node_type = h.slug_to_node_type(slug)
    q = '''                   
        MATCH (node:{node_type})
        RETURN node.handle_id, node.name
        ORDER BY node.name
        '''.format(node_type=node_type.type.replace(' ', '_'))
    with nc.neo4jdb.transaction as r:
        type_list = r.execute(q).fetchall()
    return HttpResponse(json.dumps(type_list), mimetype='application/json')


@login_required
def get_unlocated_node_type(request, slug):
    """
    Compiles a list of alla nodes of that node type that does not have a Located_in
    relationship and returns a list of node name, node id tuples.
    """
    node_type = h.slug_to_node_type(slug)
    q = '''
        MATCH (node:{node_type})
        WHERE NOT (node)-[:Located_in]->()
        RETURN node.handle_id, node.name
        ORDER BY node.name
        '''.format(node_type=node_type.type.replace(' ', '_'))
    with nc.neo4jdb.transaction as r:
        type_list = r.execute(q).fetchall()
    return HttpResponse(json.dumps(type_list), mimetype='application/json')


@login_required
def get_children(request, handle_id, slug=None):
    """
    Compiles a list of the nodes children and returns a list of
    node name, node id tuples. If node_type is set the function will only return
    nodes of that type.
    """
    nh = get_object_or_404(NodeHandle, handle_id=handle_id)
    type_filter = ''
    if slug:
        type_filter = 'and child:{node_type}'.format(node_type=h.slug_to_node_type(slug).type.replace(' ', '_'))
    q = '''                   
        MATCH (parent:Node {{handle_id:{{handle_id}}}})
        MATCH parent--child
        WHERE (parent-[:Has]->child or parent<-[:Located_in|Part_of]-child) {type_filter}
        RETURN collect(child.handle_id) as ids
        '''.format(type_filter=type_filter)
    id_list = nc.query_to_dict(nc.neo4jdb, q, handle_id=nh.handle_id)
    child_list = []
    for child_handle_id, child in NodeHandle.objects.in_bulk(id_list.get('ids')).items():
        name = '%s %s' % (child.node_type.type, child.node_name)
        child_list.append((child_handle_id, name))
    return HttpResponse(json.dumps(child_list), mimetype='application/json')


@login_required
def convert_host(request, handle_id, slug):
    """
    Convert a Host to Firewall or Switch.
    """
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    if slug in ['firewall', 'switch'] and nh.node_type.type == 'Host':
        node_type = h.slug_to_node_type(slug, create=True)
        node = nh.get_node()
        nh, node = h.logical_to_physical(request.user, node.handle_id)
        nh.node_type = node_type
        nh.save()
        node_properties = {
            'backup': ''
        }
        h.dict_update_node(request.user, node.handle_id, node_properties, node_properties.keys())
    return HttpResponseRedirect(nh.get_absolute_url())


# Edit functions
@login_required
def edit_node(request, slug, handle_id):
    """
    Generic edit function that redirects calls to node type sensitive edit 
    functions.
    """
    if not request.user.is_staff:
        raise Http404
    try:
        func = EDIT_FUNC[slug]
    except KeyError:
        raise Http404
    return func(request, handle_id)


@login_required
def edit_cable(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, cable = h.get_nh_node(handle_id)
    connections = cable.get_connected_equipment()
    relations = cable.get_relations()
    if request.POST:
        form = forms.EditCableForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, cable.handle_id, form)
            if form.cleaned_data['relationship_end_a']:
                end_a_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_a'])
                h.set_connected_to(request.user, cable, end_a_nh.handle_id)
            if form.cleaned_data['relationship_end_b']:
                end_b_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_b'])
                h.set_connected_to(request.user, cable, end_b_nh.handle_id)
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                h.set_provider(request.user, cable, owner_nh.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditCableForm(cable.data)
    return render_to_response('noclook/edit/edit_cable.html',
                              {'node_handle': nh, 'form': form, 'node': cable, 'connections': connections,
                               'relations': relations},
                              context_instance=RequestContext(request))


@login_required
def edit_customer(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, customer = h.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditCustomerForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, customer.handle_id, form)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditCustomerForm(customer.data)
    return render_to_response('noclook/edit/edit_customer.html', {'node_handle': nh, 'form': form, 'node': customer},
                              context_instance=RequestContext(request))


@login_required
def edit_end_user(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, end_user = h.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditEndUserForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, end_user.handle_id, form)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditEndUserForm(end_user.data)
    return render_to_response('noclook/edit/edit_end_user.html', {'node_handle': nh, 'form': form, 'node': end_user},
                              context_instance=RequestContext(request))


@login_required
def edit_external_equipment(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, external_equipment = h.get_nh_node(handle_id)
    relations = external_equipment.get_relations()
    location = external_equipment.get_location()
    ports = external_equipment.get_ports()
    if request.POST:
        form = forms.EditExternalEquipmentForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, external_equipment.handle_id, form)
            # External Equipment specific updates
            if form.cleaned_data['relationship_owner']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_owner'])
                h.set_owner(request.user, external_equipment, owner_nh.handle_id)
            if form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                h.set_location(request.user, external_equipment, location_nh.handle_id)
            if form.cleaned_data['relationship_ports']:
                for port_name in form.cleaned_data['relationship_ports']:
                    h.create_port(external_equipment, port_name, request.user)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditExternalEquipmentForm(external_equipment.data)
    return render_to_response('noclook/edit/edit_external_equipment.html',
                              {'node_handle': nh, 'node': external_equipment, 'form': form, 'relations': relations,
                               'location': location, 'ports': ports},
                              context_instance=RequestContext(request))


@login_required
def edit_firewall(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, firewall = h.get_nh_node(handle_id)
    location = firewall.get_location()
    relations = firewall.get_relations()
    depends_on = firewall.get_dependencies()
    host_services = firewall.get_host_services()
    ports = firewall.get_ports()
    if request.POST:
        form = forms.EditFirewallForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, firewall.handle_id, form)
            # Host specific updates
            if form.cleaned_data['relationship_user']:
                user_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_user'])
                h.set_user(request.user, firewall, user_nh.handle_id)
            if form.cleaned_data['relationship_owner']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_owner'])
                h.set_owner(request.user, firewall, owner_nh.handle_id)
            # You can not set location and depends on at the same time
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                h.set_depends_on(request.user, firewall, depends_on_nh.handle_id)
            elif form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                h.set_location(request.user, firewall, location_nh.handle_id)
            if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                h.remove_rogue_service_marker(request.user, firewall.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditFirewallForm(firewall.data)
    return render_to_response('noclook/edit/edit_firewall.html',
                              {'node_handle': nh, 'node': firewall, 'form': form, 'location': location,
                               'relations': relations, 'depends_on': depends_on, 'ports': ports,
                               'host_services': host_services}, context_instance=RequestContext(request))


@login_required
def edit_host(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, host = h.get_nh_node(handle_id)
    location = host.get_location()
    relations = host.get_relations()
    depends_on = host.get_dependencies()
    host_services = host.get_host_services()
    if request.POST:
        form = forms.EditHostForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, host.handle_id, form)
            # Host specific updates
            if form.cleaned_data['relationship_user']:
                user_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_user'])
                h.set_user(request.user, host, user_nh.handle_id)
            if form.cleaned_data['relationship_owner']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_owner'])
                h.set_owner(request.user, host, owner_nh.handle_id)
            # You can not set location and depends on at the same time
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                h.set_depends_on(request.user, host, depends_on_nh.handle_id)
            elif form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                h.set_location(request.user, host, location_nh.handle_id)
            if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                h.remove_rogue_service_marker(request.user, host.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditHostForm(host.data)
    return render_to_response('noclook/edit/edit_host.html',
                              {'node_handle': nh, 'node': host, 'form': form, 'location': location,
                               'relations': relations, 'depends_on': depends_on,
                               'host_services': host_services}, context_instance=RequestContext(request))


@login_required
def edit_odf(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, odf = h.get_nh_node(handle_id)
    location = odf.get_location()
    ports = odf.get_ports()
    if request.POST:
        form = forms.EditOdfForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, odf.handle_id, form)
            # ODF specific updates
            if form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                h.set_location(request.user, odf, location_nh.handle_id)
            if form.cleaned_data['relationship_ports']:
                for port_name in form.cleaned_data['relationship_ports']:
                    h.create_port(odf, port_name, request.user)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditOdfForm(odf.data)
    return render_to_response('noclook/edit/edit_odf.html',
                              {'node_handle': nh, 'node': odf, 'form': form, 'location': location, 'ports': ports},
                              context_instance=RequestContext(request))


@login_required
def edit_optical_link(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, link = h.get_nh_node(handle_id)
    relations = link.get_relations()
    depends_on = link.get_dependencies()
    if request.POST:
        form = forms.EditOpticalLinkForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, link.handle_id, form)
            # Optical Link node updates
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                h.set_provider(request.user, link, owner_nh.handle_id)
            if form.cleaned_data['relationship_end_a']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_a'])
                h.set_depends_on(request.user, link, depends_on_nh.handle_id)
            if form.cleaned_data['relationship_end_b']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_b'])
                h.set_depends_on(request.user, link, depends_on_nh.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditOpticalLinkForm(link.data)
    return render_to_response('noclook/edit/edit_optical_link.html',
                              {'node_handle': nh, 'form': form, 'node': link, 'relations': relations,
                               'depends_on': depends_on},
                              context_instance=RequestContext(request))

@login_required
def edit_optical_multiplex_section(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, oms = h.get_nh_node(handle_id)
    relations = oms.get_relations()
    depends_on = oms.get_dependencies()
    if request.POST:
        form = forms.EditOpticalMultiplexSectionForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, oms.handle_id, form)
            # Optical Multiplex Section node updates
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                h.set_provider(request.user, oms, owner_nh.handle_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                h.set_depends_on(request.user, oms, depends_on_nh.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditOpticalMultiplexSectionForm(oms.data)
    return render_to_response('noclook/edit/edit_optical_multiplex_section.html',
                              {'node_handle': nh, 'form': form, 'node': oms, 'relations': relations,
                               'depends_on': depends_on},
                              context_instance=RequestContext(request))


@login_required
def edit_optical_node(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, optical_node = h.get_nh_node(handle_id)
    location = optical_node.get_location()
    ports = optical_node.get_ports()
    if request.POST:
        form = forms.EditOpticalNodeForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, optical_node.handle_id, form)
            # Optical Node specific updates
            if form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                h.set_location(request.user, optical_node, location_nh.handle_id)
            if form.cleaned_data['relationship_ports']:
                for port_name in form.cleaned_data['relationship_ports']:
                    h.create_port(optical_node, port_name, request.user)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditOpticalNodeForm(optical_node.data)
    return render_to_response('noclook/edit/edit_optical_node.html',
                              {'node_handle': nh, 'node': optical_node, 'form': form, 'location': location,
                               'ports': ports},
                              context_instance=RequestContext(request))


@login_required
def edit_optical_path(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, path = h.get_nh_node(handle_id)
    relations = path.get_relations()
    depends_on = path.get_dependencies()
    if request.POST:
        form = forms.EditOpticalPathForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, path.handle_id, form)
            # Optical Path node updates
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                h.set_provider(request.user, path, owner_nh.handle_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                h.set_depends_on(request.user, path, depends_on_nh.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditOpticalPathForm(path.data)
    return render_to_response('noclook/edit/edit_optical_path.html',
                              {'node_handle': nh, 'form': form, 'node': path, 'relations': relations,
                               'depends_on': depends_on},
                              context_instance=RequestContext(request))


@login_required
def edit_peering_partner(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, peering_partner = h.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditPeeringPartnerForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, peering_partner.handle_id, form)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditPeeringPartnerForm(peering_partner.data)
    return render_to_response('noclook/edit/edit_peering_partner.html',
                              {'node_handle': nh, 'node': peering_partner, 'form': form},
                              context_instance=RequestContext(request))


@login_required
def edit_port(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    nh, port = h.get_nh_node(handle_id)
    parent = port.get_parent()
    if request.POST:
        form = forms.EditPortForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, port.handle_id, form)
            # Port specific updates
            if form.cleaned_data['relationship_parent']:
                parent_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_parent'])
                h.set_has(request.user, parent_nh.get_node(), port.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditPortForm(port.data)
    return render_to_response('noclook/edit/edit_port.html',
                              {'node_handle': nh, 'form': form, 'node': port, 'parent': parent},
                              context_instance=RequestContext(request))


@login_required
def edit_provider(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, provider = h.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditProviderForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, provider.handle_id, form)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditProviderForm(provider.data)
    return render_to_response('noclook/edit/edit_provider.html',
                              {'node_handle': nh, 'form': form, 'node': provider},
                              context_instance=RequestContext(request))


@login_required
def edit_rack(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, rack = h.get_nh_node(handle_id)
    parent = rack.get_parent()
    located_in = rack.get_located_in()
    if request.POST:
        form = forms.EditRackForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, rack.handle_id, form)
            # Rack specific updates
            if form.cleaned_data['relationship_parent']:
                parent_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_parent'])
                h.set_has(request.user, parent_nh.get_node(), rack.handle_id)
            if form.cleaned_data['relationship_located_in']:
                equipment = NodeHandle.objects.get(pk=form.cleaned_data['relationship_located_in'])
                h.set_location(request.user, equipment.get_node(), rack.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditRackForm(rack.data)
    return render_to_response('noclook/edit/edit_rack.html',
                              {'node_handle': nh, 'form': form, 'parent': parent, 'node': rack,
                               'located_in': located_in},
                              context_instance=RequestContext(request))


@login_required
def edit_router(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, router = h.get_nh_node(handle_id)
    location = router.get_location()
    if request.POST:
        form = forms.EditRouterForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, router.handle_id, form)
            # Router specific updates
            if form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                h.set_location(request.user, router, location_nh.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditRouterForm(router.data)
        return render_to_response('noclook/edit/edit_router.html',
                                  {'node_handle': nh, 'node': router, 'form': form, 'location': location},
                                  context_instance=RequestContext(request))


@login_required
def edit_service(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, service = h.get_nh_node(handle_id)
    relations = service.get_relations()
    depends_on = service.get_dependencies()
    if request.POST:
        form = forms.EditServiceForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, service.handle_id, form)
            # Service node updates
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                h.set_provider(request.user, service, owner_nh.handle_id)
            if form.cleaned_data['relationship_user']:
                user_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_user'])
                h.set_user(request.user, service, user_nh.handle_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                h.set_depends_on(request.user, service, depends_on_nh.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditServiceForm(service.data)
    return render_to_response('noclook/edit/edit_service.html',
                              {'node_handle': nh, 'form': form, 'node': service, 'relations': relations,
                               'depends_on': depends_on},
                              context_instance=RequestContext(request))


@login_required
def edit_switch(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, switch = h.get_nh_node(handle_id)
    location = switch.get_location()
    relations = switch.get_relations()
    depends_on = switch.get_dependencies()
    host_services = switch.get_host_services()
    ports = switch.get_ports()
    if request.POST:
        form = forms.EditSwitchForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, switch.handle_id, form)
            # Host specific updates
            if form.cleaned_data['relationship_user']:
                user_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_user'])
                h.set_user(request.user, switch, user_nh.handle_id)
            if form.cleaned_data['relationship_owner']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_owner'])
                h.set_owner(request.user, switch, owner_nh.handle_id)
            # You can not set location and depends on at the same time
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                h.set_depends_on(request.user, switch, depends_on_nh.handle_id)
            elif form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                h.set_location(request.user, switch, location_nh.handle_id)
            if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                h.remove_rogue_service_marker(request.user, switch.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditSwitchForm(switch.data)
    return render_to_response('noclook/edit/edit_switch.html',
                              {'node_handle': nh, 'node': switch, 'form': form, 'location': location,
                               'relations': relations, 'depends_on': depends_on, 'ports': ports,
                               'host_services': host_services}, context_instance=RequestContext(request))


# TODO: Fix below
@login_required
def edit_site(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    site_owner = h.iter2list(node.Responsible_for.incoming)
    if request.POST:
        form = forms.EditSiteForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Site specific updates
            if form.cleaned_data['name'].upper() != node['name']:
                pre_value = node['name']
                with nc.neo4jdb.transaction:
                    node['name'] = form.cleaned_data['name'].upper()

                    nh.node_name = node['name']
                    nh.save()
                    activitylog.update_node_property(
                        request.user,
                        nh,
                        'name',
                        pre_value,
                        form.cleaned_data['name'].upper()
                    )
                # Update search index
                index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
                nc.update_index_item(nc.neo4jdb, index, node, 'name')
            if form.cleaned_data['country']:
                inverse_cm = dict((forms.COUNTRY_MAP[key], key) for key  in forms.COUNTRY_MAP)
                with nc.neo4jdb.transaction:
                    node['country_code'] = inverse_cm[node['country']]
            # Set site owner
            if form.cleaned_data['relationship_site_owner']:
                h.set_responsible_for(request.user, node, form.cleaned_data['relationship_site_owner'])
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_site.html',
                                  {'node': node, 'form': form,
                                   'site_owner': site_owner},
                                context_instance=RequestContext(request))
    else:
        form = forms.EditSiteForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_site.html',
                                  {'form': form, 'site_owner': site_owner,
                                   'node': node},
                                context_instance=RequestContext(request))

@login_required
def edit_site_owner(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditSiteOwnerForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_site_owner.html',
                                  {'node': node, 'form': form},
                                context_instance=RequestContext(request))
    else:
        form = forms.EditSiteOwnerForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_site_owner.html',
                                  {'form': form, 'node': node},
                                context_instance=RequestContext(request))


EDIT_FUNC = {
    'cable': edit_cable,
    'customer': edit_customer,
    'end-user': edit_end_user,
    'external-equipment': edit_external_equipment,
    'firewall': edit_firewall,
    'service': edit_service,
    'host': edit_host,
    'odf': edit_odf,
    'optical-node': edit_optical_node,
    'optical-link': edit_optical_link,
    'optical-multiplex-section': edit_optical_multiplex_section,
    'optical-path': edit_optical_path,
    'peering-partner': edit_peering_partner,
    'port': edit_port,
    'provider': edit_provider,
    'rack': edit_rack,
    'router': edit_router,
    'site': edit_site,
    'site-owner': edit_site_owner,
    'switch': edit_switch,
}
