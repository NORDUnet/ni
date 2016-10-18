# -*- coding: utf-8 -*-
"""
Created on Wed Dec 14 14:00:03 2011

@author: lundberg

Node manipulation views.
"""
from operator import itemgetter
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse, HttpResponseForbidden
from django.shortcuts import render_to_response, get_object_or_404, render
from django.template import RequestContext
import json
from apps.noclook.models import NodeHandle
from apps.noclook import forms
from apps.noclook import activitylog
from apps.noclook import helpers
import norduniclient as nc


# Helper functions
@login_required
def delete_node(request, slug, handle_id):
    """
    Removes the node and all its relationships.
    """
    if not request.user.is_staff:
        return HttpResponseForbidden()
    redirect = '/{}'.format(slug)
    nh, node = helpers.get_nh_node(handle_id)
    try:
        # Redirect to parent if deleted node was a child node
        parent = node.get_parent().get('Has', [])
        if parent:
            redirect = helpers.get_node_url(parent[0]['node'].handle_id)
    except AttributeError:
        pass
    helpers.delete_node(request.user, node.handle_id)
    return HttpResponseRedirect(redirect)


@login_required
def delete_relationship(request, slug, handle_id, rel_id):
    """
    Removes the relationship if the node has a relationship matching the
    supplied id.
    """
    if not request.user.is_staff:
        return HttpResponseForbidden()
    success = False
    if request.method == 'POST':
        nh, node = helpers.get_nh_node(handle_id)
        try:
            relationship = nc.get_relationship_model(nc.neo4jdb, rel_id)
            if node.handle_id == relationship.start or node.handle_id == relationship.end:
                activitylog.delete_relationship(request.user, relationship)
                relationship.delete()
                success = True
        except nc.exceptions.RelationshipNotFound:
            success = True
    return JsonResponse({'success': success, 'relationship_id': '{}'.format(rel_id)})


@login_required
def update_relationship(request, slug, handle_id, rel_id):
    """
    Removes the relationship if the node has a relationship matching the
    supplied id.
    """
    if not request.user.is_staff:
        return HttpResponseForbidden()
    success = False
    properties = {}
    if request.POST:
        nh, node = helpers.get_nh_node(handle_id)
        try:
            for key, value in request.POST.iteritems():
                properties[key] = json.loads(value)
            relationship = nc.get_relationship_model(nc.neo4jdb, rel_id)
            if node.handle_id == relationship.start or node.handle_id == relationship.end:
                success = helpers.dict_update_relationship(request.user, relationship.id, properties)
        except nc.exceptions.RelationshipNotFound:
            success = True
        except ValueError:
            pass
    return JsonResponse({'success': success, 'relationship_id': '{}'.format(rel_id), 'data': properties})


# Form data returns
@login_required
def get_node_type(request, slug):
    """
    Compiles a list of alla nodes of that node type and returns a list of
    node name, node id tuples.
    """
    node_type = helpers.slug_to_node_type(slug)
    q = '''                   
        MATCH (node:{node_type})
        RETURN node.handle_id, node.name
        ORDER BY node.name
        '''.format(node_type=node_type.type.replace(' ', '_'))
    with nc.neo4jdb.transaction as r:
        type_list = r.execute(q).fetchall()
    return JsonResponse(type_list, safe=False)


@login_required
def get_unlocated_node_type(request, slug):
    """
    Compiles a list of alla nodes of that node type that does not have a Located_in
    relationship and returns a list of node name, node id tuples.
    """
    node_type = helpers.slug_to_node_type(slug)
    q = '''
        MATCH (node:{node_type})
        WHERE NOT (node)-[:Located_in]->()
        RETURN node.handle_id, node.name
        ORDER BY node.name
        '''.format(node_type=node_type.type.replace(' ', '_'))
    with nc.neo4jdb.transaction as r:
        type_list = r.execute(q).fetchall()
    return JsonResponse(type_list, safe=False)


@login_required
def get_child_form_data(request, handle_id, slug=None):
    """
    Compiles a list of the nodes children and returns a list of
    node name, node id tuples. If node_type is set the function will only return
    nodes of that type.
    """
    nh = get_object_or_404(NodeHandle, handle_id=handle_id)
    node_type = slug
    if slug:
        node_type = helpers.slug_to_node_type(slug).type.replace(' ', '_')
    child_list = []
    for child in nh.get_node().get_child_form_data(node_type):
        if not slug:
            node_type = helpers.labels_to_node_type(child['labels'])
        name = u'{} {}'.format(node_type.replace('_', ' '), child['name'])
        if child.get('description', None):
            name = u'{} ({})'.format(name, child['description'])
        child_list.append((child['handle_id'], name))
        child_list = sorted(child_list, key=itemgetter(1))
    return JsonResponse(child_list, safe=False)


@login_required
def get_subtype_form_data(request, slug, key, value):
    """
    Compiles a list of the nodes children and returns a list of
    node name, node id tuples. If node_type is set the function will only return
    nodes of that type.
    """
    node_type = helpers.slug_to_node_type(slug).type.replace(' ', '_')
    q = """
        MATCH (n:{node_type})
        WHERE n.{key} = '{value}'
        RETURN n.handle_id as handle_id, n.name as name, n.description as description
        ORDER BY n.name
        """.format(node_type=node_type, key=key, value=value)
    subtype_list = []
    for subtype in nc.query_to_list(nc.neo4jdb, q):
        name = subtype['name']
        if subtype.get('description', None):
            name = u'{} ({})'.format(name, subtype['description'])
        subtype_list.append((subtype['handle_id'], name))
        subtype_list = sorted(subtype_list, key=itemgetter(1))
    return JsonResponse(subtype_list, safe=False)


@login_required
def convert_host(request, handle_id, slug):
    """
    Convert a Host to Firewall or Switch.
    """
    if not request.user.is_staff:
        return HttpResponseForbidden()
    allowed_types = ['firewall', 'switch', 'pdu']  # Types that can be added as Hosts by nmap
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    if slug in allowed_types and nh.node_type.type == 'Host':
        node_type = helpers.slug_to_node_type(slug, create=True)
        nh, node = helpers.logical_to_physical(request.user, handle_id)
        node.switch_type(nh.node_type.get_label(), node_type.get_label())
        nh.node_type = node_type
        nh.save()
        node_properties = {
            'backup': ''
        }
        helpers.dict_update_node(request.user, node.handle_id, node_properties, node_properties.keys())
    return HttpResponseRedirect(nh.get_absolute_url())


# Edit functions
@login_required
def edit_node(request, slug, handle_id):
    """
    Generic edit function that redirects calls to node type sensitive edit 
    functions.
    """
    if not request.user.is_staff:
        return HttpResponseForbidden()
    try:
        func = EDIT_FUNC[slug]
    except KeyError:
        raise Http404
    return func(request, handle_id)


@login_required
def edit_cable(request, handle_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    # Get needed data from node
    nh, cable = helpers.get_nh_node(handle_id)
    connections = cable.get_connected_equipment()
    relations = cable.get_relations()
    if request.POST:
        form = forms.EditCableForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, cable.handle_id, form)
            if form.cleaned_data['relationship_end_a']:
                end_a_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_a'])
                helpers.set_connected_to(request.user, cable, end_a_nh.handle_id)
            if form.cleaned_data['relationship_end_b']:
                end_b_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_b'])
                helpers.set_connected_to(request.user, cable, end_b_nh.handle_id)
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, cable, owner_nh.handle_id)
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
        return HttpResponseForbidden()
    # Get needed data from node
    nh, customer = helpers.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditCustomerForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, customer.handle_id, form)
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
        return HttpResponseForbidden()
    # Get needed data from node
    nh, end_user = helpers.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditEndUserForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, end_user.handle_id, form)
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
        return HttpResponseForbidden()
    # Get needed data from node
    nh, external_equipment = helpers.get_nh_node(handle_id)
    relations = external_equipment.get_relations()
    location = external_equipment.get_location()
    ports = external_equipment.get_ports()
    if request.POST:
        form = forms.EditExternalEquipmentForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, external_equipment.handle_id, form)
            # External Equipment specific updates
            if form.cleaned_data['relationship_owner']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_owner'])
                helpers.set_owner(request.user, external_equipment, owner_nh.handle_id)
            if form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                helpers.set_location(request.user, external_equipment, location_nh.handle_id)
            if form.cleaned_data['relationship_ports']:
                for port_name in form.cleaned_data['relationship_ports']:
                    helpers.create_port(external_equipment, port_name, request.user)
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
        return HttpResponseForbidden()
    # Get needed data from node
    nh, firewall = helpers.get_nh_node(handle_id)
    location = firewall.get_location()
    relations = firewall.get_relations()
    depends_on = firewall.get_dependencies()
    host_services = firewall.get_host_services()
    ports = firewall.get_ports()
    if request.POST:
        form = forms.EditFirewallForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, firewall.handle_id, form)
            #  Firewall specific updates
            if form.cleaned_data['relationship_user']:
                user_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_user'])
                helpers.set_user(request.user, firewall, user_nh.handle_id)
            if form.cleaned_data['relationship_owner']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_owner'])
                helpers.set_owner(request.user, firewall, owner_nh.handle_id)
            # You can not set location and depends on at the same time
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                helpers.set_depends_on(request.user, firewall, depends_on_nh.handle_id)
            elif form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                helpers.set_location(request.user, firewall, location_nh.handle_id)
            if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                helpers.remove_rogue_service_marker(request.user, firewall.handle_id)
            if form.cleaned_data['relationship_ports']:
                for port_name in form.cleaned_data['relationship_ports']:
                    helpers.create_port(firewall, port_name, request.user)
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
        return HttpResponseForbidden()
    # Get needed data from node
    nh, host = helpers.get_nh_node(handle_id)
    location = host.get_location()
    relations = host.get_relations()
    depends_on = host.get_dependencies()
    host_services = host.get_host_services()
    ports = host.get_ports()
    if request.POST:
        form = forms.EditHostForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, host.handle_id, form)
            # Host specific updates
            if form.cleaned_data['relationship_user']:
                    user_nh = _nh_safe_get(form.cleaned_data['relationship_user'])
                    if user_nh:
                        helpers.set_user(request.user, host, user_nh.handle_id)
            if form.cleaned_data['relationship_owner']:
                owner_nh = _nh_safe_get(form.cleaned_data['relationship_owner'])
                if owner_nh:
                    helpers.set_owner(request.user, host, owner_nh.handle_id)
            # You can not set location and depends on at the same time
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = _nh_safe_get(form.cleaned_data['relationship_depends_on'])
                if depends_on_nh:
                    helpers.set_depends_on(request.user, host, depends_on_nh.handle_id)
            elif form.cleaned_data['relationship_location']:
                location_nh = _nh_safe_get(form.cleaned_data['relationship_location'])
                if location_nh:
                    helpers.set_location(request.user, host, location_nh.handle_id)
            if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                helpers.remove_rogue_service_marker(request.user, host.handle_id)
            if form.cleaned_data['relationship_ports']:
                for port_name in form.cleaned_data['relationship_ports']:
                    helpers.create_port(host, port_name, request.user)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditHostForm(host.data)
    return render_to_response('noclook/edit/edit_host.html',
                              {'node_handle': nh, 'node': host, 'form': form, 'location': location,
                               'relations': relations, 'depends_on': depends_on, 'ports': ports,
                               'host_services': host_services}, context_instance=RequestContext(request))
def _nh_safe_get(pk):
    try:
        nh = NodeHandle.objects.get(pk=pk)
    except:
        nh = None
    return nh

@login_required
def edit_odf(request, handle_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    # Get needed data from node
    nh, odf = helpers.get_nh_node(handle_id)
    location = odf.get_location()
    ports = odf.get_ports()
    if request.POST:
        form = forms.EditOdfForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, odf.handle_id, form)
            # ODF specific updates
            if form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                helpers.set_location(request.user, odf, location_nh.handle_id)
            if form.cleaned_data['relationship_ports']:
                for port_name in form.cleaned_data['relationship_ports']:
                    helpers.create_port(odf, port_name, request.user)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditOdfForm(odf.data)
    return render_to_response('noclook/edit/edit_odf.html',
                              {'node_handle': nh, 'node': odf, 'form': form, 'location': location, 'ports': ports},
                              context_instance=RequestContext(request))

@staff_member_required
def edit_optical_fillter(request, handle_id):
    nh, of = helpers.get_nh_node(handle_id)
    location = of.get_location()
    ports = of.get_ports()
    form = forms.EditOpticalFilterForm(request.POST or of.data)
    if request.POST and form.is_valid():
        # Generic node update
        helpers.form_update_node(request.user, of.handle_id, form)
        # ODF specific updates
        if form.cleaned_data['relationship_location']:
            location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
            helpers.set_location(request.user, of, location_nh.handle_id)
        if form.cleaned_data['relationship_ports']:
            for port_name in form.cleaned_data['relationship_ports']:
                helpers.create_port(of, port_name, request.user)
        if 'saveanddone' in request.POST:
            return HttpResponseRedirect(nh.get_absolute_url())
        else:
            return HttpResponseRedirect('%sedit' % nh.get_absolute_url())

    return render(request, 'noclook/edit/edit_optical_filter.html', {'node_handle': nh, 'node': of, 'form': form, 'location': location, 'ports': ports})


@login_required
def edit_optical_link(request, handle_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    # Get needed data from node
    nh, link = helpers.get_nh_node(handle_id)
    relations = link.get_relations()
    depends_on = link.get_dependencies()
    if request.POST:
        form = forms.EditOpticalLinkForm(request.POST)
        if form.is_valid():
            if 'type' in form.cleaned_data:
              form.cleaned_data['type'] = form.cleaned_data['type'].name
            # Generic node update
            helpers.form_update_node(request.user, link.handle_id, form)
            # Optical Link node updates
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, link, owner_nh.handle_id)
            if form.cleaned_data['relationship_end_a']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_a'])
                helpers.set_depends_on(request.user, link, depends_on_nh.handle_id)
            if form.cleaned_data['relationship_end_b']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_b'])
                helpers.set_depends_on(request.user, link, depends_on_nh.handle_id)
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
        return HttpResponseForbidden()
    # Get needed data from node
    nh, oms = helpers.get_nh_node(handle_id)
    relations = oms.get_relations()
    depends_on = oms.get_dependencies()
    if request.POST:
        form = forms.EditOpticalMultiplexSectionForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, oms.handle_id, form)
            # Optical Multiplex Section node updates
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, oms, owner_nh.handle_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                helpers.set_depends_on(request.user, oms, depends_on_nh.handle_id)
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
        return HttpResponseForbidden()
    # Get needed data from node
    nh, optical_node = helpers.get_nh_node(handle_id)
    location = optical_node.get_location()
    ports = optical_node.get_ports()
    if request.POST:
        form = forms.EditOpticalNodeForm(request.POST)
        if form.is_valid():
            if "type" in form.cleaned_data and form.cleaned_data["type"]:
                form.cleaned_data['type'] = form.cleaned_data['type'].name
            # Generic node update
            helpers.form_update_node(request.user, optical_node.handle_id, form)
            # Optical Node specific updates
            if form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                helpers.set_location(request.user, optical_node, location_nh.handle_id)
            if form.cleaned_data['relationship_ports']:
                for port_name in form.cleaned_data['relationship_ports']:
                    helpers.create_port(optical_node, port_name, request.user)
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
        return HttpResponseForbidden()
    # Get needed data from node
    nh, path = helpers.get_nh_node(handle_id)
    relations = path.get_relations()
    depends_on = path.get_dependencies()
    if request.POST:
        form = forms.EditOpticalPathForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, path.handle_id, form)
            # Optical Path node updates
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, path, owner_nh.handle_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                helpers.set_depends_on(request.user, path, depends_on_nh.handle_id)
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
def edit_pdu(request, handle_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    # Get needed data from node
    nh, pdu = helpers.get_nh_node(handle_id)
    location = pdu.get_location()
    relations = pdu.get_relations()
    depends_on = pdu.get_dependencies()
    host_services = pdu.get_host_services()
    ports = pdu.get_ports()
    if request.POST:
        form = forms.EditPDUForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, pdu.handle_id, form)
            # Host specific updates
            if form.cleaned_data['relationship_user']:
                user_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_user'])
                helpers.set_user(request.user, pdu, user_nh.handle_id)
            if form.cleaned_data['relationship_owner']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_owner'])
                helpers.set_owner(request.user, pdu, owner_nh.handle_id)
            # You can not set location and depends on at the same time
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                helpers.set_depends_on(request.user, pdu, depends_on_nh.handle_id)
            elif form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                helpers.set_location(request.user, pdu, location_nh.handle_id)
            if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                helpers.remove_rogue_service_marker(request.user, pdu.handle_id)
            if form.cleaned_data['relationship_ports']:
                for port_name in form.cleaned_data['relationship_ports']:
                    helpers.create_port(pdu, port_name, request.user)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditSwitchForm(pdu.data)
    return render_to_response('noclook/edit/edit_pdu.html',
                              {'node_handle': nh, 'node': pdu, 'form': form, 'location': location,
                               'relations': relations, 'depends_on': depends_on, 'ports': ports,
                               'host_services': host_services}, context_instance=RequestContext(request))


@login_required
def edit_peering_partner(request, handle_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    # Get needed data from node
    nh, peering_partner = helpers.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditPeeringPartnerForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, peering_partner.handle_id, form)
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
        return HttpResponseForbidden()
    nh, port = helpers.get_nh_node(handle_id)
    parent = port.get_parent()
    connected_to = port.get_connected_to()
    if request.POST:
        form = forms.EditPortForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, port.handle_id, form)
            # Port specific updates
            if form.cleaned_data['relationship_parent']:
                parent_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_parent'])
                helpers.set_has(request.user, parent_nh.get_node(), port.handle_id)
            if form.cleaned_data['relationship_connected_to']:
                cable_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_connected_to'])
                helpers.set_connected_to(request.user, cable_nh.get_node(), port.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditPortForm(port.data)
    return render_to_response('noclook/edit/edit_port.html',
                              {'node_handle': nh, 'form': form, 'node': port, 'parent': parent,
                               'connected_to': connected_to}, context_instance=RequestContext(request))


@login_required
def edit_provider(request, handle_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    # Get needed data from node
    nh, provider = helpers.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditProviderForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, provider.handle_id, form)
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
        return HttpResponseForbidden()
    # Get needed data from node
    nh, rack = helpers.get_nh_node(handle_id)
    parent = rack.get_parent()
    located_in = rack.get_located_in()
    if request.POST:
        form = forms.EditRackForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, rack.handle_id, form)
            # Rack specific updates
            if form.cleaned_data['relationship_parent']:
                parent_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_parent'])
                helpers.set_has(request.user, parent_nh.get_node(), rack.handle_id)
            if form.cleaned_data['relationship_located_in']:
                equipment = NodeHandle.objects.get(pk=form.cleaned_data['relationship_located_in'])
                helpers.set_location(request.user, equipment.get_node(), rack.handle_id)
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
        return HttpResponseForbidden()
    # Get needed data from node
    nh, router = helpers.get_nh_node(handle_id)
    location = router.get_location()
    if request.POST:
        form = forms.EditRouterForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, router.handle_id, form)
            # Router specific updates
            if form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                helpers.set_location(request.user, router, location_nh.handle_id)
            if form.cleaned_data['relationship_ports']:
                for port_name in form.cleaned_data['relationship_ports']:
                    helpers.create_port(router, port_name, request.user)
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
        return HttpResponseForbidden()
    # Get needed data from node
    nh, service = helpers.get_nh_node(handle_id)
    relations = service.get_relations()
    depends_on = service.get_dependencies()
    if request.POST:
        form = forms.EditServiceForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, service.handle_id, form)
            # Service node updates
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, service, owner_nh.handle_id)
            if form.cleaned_data['relationship_user']:
                user_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_user'])
                helpers.set_user(request.user, service, user_nh.handle_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                helpers.set_depends_on(request.user, service, depends_on_nh.handle_id)
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
def edit_site(request, handle_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    # Get needed data from node
    nh, site = helpers.get_nh_node(handle_id)
    relations = site.get_relations()
    if request.POST:
        form = forms.EditSiteForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, site.handle_id, form)
            # Set site owner
            if form.cleaned_data['relationship_responsible_for']:
                responsible_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_responsible_for'])
                helpers.set_responsible_for(request.user, site, responsible_nh.handle_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditSiteForm(site.data)
    return render_to_response('noclook/edit/edit_site.html',
                              {'node_handle': nh, 'form': form, 'relations': relations, 'node': site},
                              context_instance=RequestContext(request))


@login_required
def edit_site_owner(request, handle_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    # Get needed data from node
    nh, site_owner = helpers.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditSiteOwnerForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, site_owner.handle_id, form)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditSiteOwnerForm(site_owner.data)
    return render_to_response('noclook/edit/edit_site_owner.html',
                              {'node_handle': nh, 'form': form, 'node': site_owner},
                              context_instance=RequestContext(request))


@login_required
def edit_switch(request, handle_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    # Get needed data from node
    nh, switch = helpers.get_nh_node(handle_id)
    location = switch.get_location()
    relations = switch.get_relations()
    depends_on = switch.get_dependencies()
    host_services = switch.get_host_services()
    ports = switch.get_ports()
    if request.POST:
        form = forms.EditSwitchForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, switch.handle_id, form)
            # Host specific updates
            if form.cleaned_data['relationship_user']:
                user_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_user'])
                helpers.set_user(request.user, switch, user_nh.handle_id)
            if form.cleaned_data['relationship_owner']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_owner'])
                helpers.set_owner(request.user, switch, owner_nh.handle_id)
            # You can not set location and depends on at the same time
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                helpers.set_depends_on(request.user, switch, depends_on_nh.handle_id)
            elif form.cleaned_data['relationship_location']:
                location_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_location'])
                helpers.set_location(request.user, switch, location_nh.handle_id)
            if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                helpers.remove_rogue_service_marker(request.user, switch.handle_id)
            if form.cleaned_data['relationship_ports']:
                for port_name in form.cleaned_data['relationship_ports']:
                    helpers.create_port(switch, port_name, request.user)
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


EDIT_FUNC = {
    'cable': edit_cable,
    'customer': edit_customer,
    'end-user': edit_end_user,
    'external-equipment': edit_external_equipment,
    'firewall': edit_firewall,
    'service': edit_service,
    'host': edit_host,
    'odf': edit_odf,
    'optical-filter': edit_optical_fillter,
    'optical-node': edit_optical_node,
    'optical-link': edit_optical_link,
    'optical-multiplex-section': edit_optical_multiplex_section,
    'optical-path': edit_optical_path,
    'pdu': edit_pdu,
    'peering-partner': edit_peering_partner,
    'port': edit_port,
    'provider': edit_provider,
    'rack': edit_rack,
    'router': edit_router,
    'site': edit_site,
    'site-owner': edit_site_owner,
    'switch': edit_switch,
}
