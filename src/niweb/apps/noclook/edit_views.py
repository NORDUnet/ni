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
from django.forms.util import ErrorDict, ErrorList
import json
from django.conf import settings as django_settings
from niweb.apps.noclook.models import NodeHandle, NodeType
from niweb.apps.noclook import forms
from niweb.apps.noclook import activitylog
import niweb.apps.noclook.helpers as h
from norduni_client_exceptions import UniqueNodeError, NoRelationshipPossible
import norduni_client as nc

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
    rel = nc.get_relationship_by_id(nc.neo4jdb, rel_id)
    if rel.start.id == node.id or rel.end.id == node.id:
        activitylog.delete_relationship(request.user, rel)
        if nc.delete_relationship(nc.neo4jdb, rel):
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
        START node=node:node_types(node_type="%s")
        RETURN node
        ORDER BY node.name
        ''' % node_type
    hits = nc.neo4jdb.query(q)
    type_list = [(hit['node'].getId(), hit['node']['name']) for hit in hits]
    return HttpResponse(json.dumps(type_list), mimetype='application/json')


@login_required
def get_unlocated_node_type(request, slug):
    """
    Compiles a list of alla nodes of that node type that does not have a Located_in
    relationship and returns a list of node name, node id tuples.
    """
    node_type = h.slug_to_node_type(slug)
    q = '''
        START node=node:node_types(node_type="%s")
        MATCH node-[r?:Located_in]-location
        WHERE r IS NULL
        RETURN node
        ORDER BY node.name
        ''' % node_type
    hits = nc.neo4jdb.query(q)
    type_list = [(hit['node'].getId(), hit['node']['name']) for hit in hits]
    return HttpResponse(json.dumps(type_list), mimetype='application/json')


@login_required
def get_children(request, node_id, slug=None):
    """
    Compiles a list of the nodes children and returns a list of
    node name, node id tuples. If node_type is set the function will only return
    nodes of that type.
    """
    type_filter = ''
    if slug:
        type_filter = 'and child.node_type = "%s"' % h.slug_to_node_type(slug)
    q = '''                   
        START parent=node({id})
        MATCH parent--child
        WHERE (parent-[:Has]->child or parent<-[:Located_in|Part_of]-child) %s
        RETURN child
        ORDER BY child.node_type, child.name
        ''' % type_filter
    hits = nc.neo4jdb.query(q, id=int(node_id))
    child_list = []
    try:
        for hit in hits:
            name = '%s %s' % (hit['child']['node_type'], hit['child']['name'])
            child_list.append((hit['child'].id, name))
    except AttributeError:
        pass
    return HttpResponse(json.dumps(child_list), mimetype='application/json')

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

@login_required
def edit_cable(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    connections = h.get_connected_cables(node)
    if request.POST:
        form = forms.EditCableForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Cable specific update
            if form.cleaned_data['telenor_trunk_id']:
                if node['name'] != form.cleaned_data['telenor_trunk_id']:
                    pre_value = node['name']
                    with nc.neo4jdb.transaction:
                        node['name'] = form.cleaned_data['telenor_trunk_id']
                        nh.node_name = form.cleaned_data['telenor_trunk_id']
                        nh.save()
                        activitylog.update_node_property(
                            request.user,
                            nh,
                            'name',
                            pre_value,
                            form.cleaned_data['telenor_trunk_id']
                        )
            # Update search index for name
            index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
            nc.update_index_item(nc.neo4jdb, index, node, 'name')
            if form.cleaned_data['relationship_end_a']:
                end_a = form.cleaned_data['relationship_end_a']
                h.connect_physical(request.user, node, end_a)
            if form.cleaned_data['relationship_end_b']:
                end_b = form.cleaned_data['relationship_end_b']
                h.connect_physical(request.user, node, end_b)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_cable.html',
                                  {'node': node, 'form': form,
                                   'connections': connections},
                                context_instance=RequestContext(request))
    else:
        form = forms.EditCableForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_cable.html',
                                  {'form': form, 'node': node,
                                   'connections': connections},
                                context_instance=RequestContext(request))
                                
@login_required
def edit_optical_node(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    ports = h.iter2list(h.get_ports(node))
    location = h.iter2list(h.get_location(node))
    if request.POST:
        form = forms.EditOpticalNodeForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Optical Node specific updates
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(request.user, nh, node, location_id)
            if form.cleaned_data['relationship_ports']:
                for port in form.cleaned_data['relationship_ports']:
                    h.create_port(node, port, request.user)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_optical_node.html',
                                      {'node': node, 'form': form, 'location': location,
                                       'ports': ports},
                                      context_instance=RequestContext(request))
    else:
        form = forms.EditOpticalNodeForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_optical_node.html',
                                  {'node': node, 'form': form, 'location': location,
                                   'ports': ports},
                                  context_instance=RequestContext(request))
@login_required        
def edit_peering_partner(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditPeeringPartnerForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_peering_partner.html',
                                  {'node': node, 'form': form},
                                context_instance=RequestContext(request))
    else:
        form = forms.EditPeeringPartnerForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_peering_partner.html',
                                  {'node': node, 'form': form},
                                context_instance=RequestContext(request))

@login_required        
def edit_rack(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    location = h.iter2list(h.get_place(node))
    located_in = h.iter2list(node.Located_in.incoming)
    if request.POST:
        form = forms.EditRackForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Rack specific updates
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                h.place_child_in_parent(request.user, node, location_id)
            if form.cleaned_data['relationship_located_in']:
                phys_node = nc.get_node_by_id(nc.neo4jdb, form.cleaned_data['relationship_located_in'])
                phys_nh = NodeHandle.objects.get(pk=phys_node['handle_id'])
                h.place_physical_in_location(request.user, phys_nh, phys_node, node.getId())
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_rack.html',
                                      {'node': node, 'form': form, 'location': location,
                                       'located_in': located_in},
                                      context_instance=RequestContext(request))
    else:
        form = forms.EditRackForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_rack.html',
                                  {'form': form, 'location': location, 'node': node,
                                   'located_in': located_in},
                                  context_instance=RequestContext(request))


@login_required        
def edit_host(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    location = h.iter2list(h.get_location(node))
    owner_relationships = h.iter2list(node.Owns.incoming)    # Physical hosts
    user_relationships = h.iter2list(node.Uses.incoming)     # Logical hosts
    service_relationships = h.iter2list(node.Depends_on.incoming)
    if request.POST:
        form = forms.EditHostForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Host specific updates
            if form.cleaned_data['relationship_user']:
                user_id = form.cleaned_data['relationship_user']
                node = h.set_user(request.user, node, user_id)
            if form.cleaned_data['relationship_owner']:
                owner_id = form.cleaned_data['relationship_owner']
                node = h.set_owner(request.user, node, owner_id)
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(request.user, nh, node, location_id)
            if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                h.remove_rogue_service_marker(request.user, node)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_host.html',
                                      {'node_handle': nh, 'node': node, 'form': form, 'location': location,
                                       'owner_relationships': owner_relationships,
                                       'user_relationships': user_relationships,
                                       'service_relationships': service_relationships},
                                      context_instance=RequestContext(request))
    else:
        form = forms.EditHostForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_host.html',
                                  {'node_handle': nh, 'node': node, 'form': form, 'location': location,
                                   'owner_relationships': owner_relationships,
                                   'user_relationships': user_relationships,
                                   'service_relationships': service_relationships},
                                  context_instance=RequestContext(request))


@login_required
def convert_host(request, handle_id, slug):
    """
    Convert a Host to Firewall or Switch.
    """
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    if slug in ['firewall', 'switch'] and nh.node_type.type == 'Host':
        node_type = h.slug_to_node_type(slug, create=True)
        node = nh.get_node()
        nh, node = h.logical_to_physical(request.user, nh, node)
        nh.node_type = node_type
        nh.save()
        node_properties = {
            'node_type': node_type.type,
            'backup': ''
        }
        h.dict_update_node(request.user, node, node_properties, node_properties.keys())
    return HttpResponseRedirect(nh.get_absolute_url())


@login_required
def edit_firewall(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    location = h.iter2list(h.get_location(node))
    owner_relationships = h.iter2list(node.Owns.incoming)
    service_relationships = h.iter2list(node.Depends_on.incoming)
    if request.POST:
        form = forms.EditFirewallForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Firewall specific updates
            if form.cleaned_data['relationship_owner']:
                owner_id = form.cleaned_data['relationship_owner']
                node = h.set_owner(request.user, node, owner_id)
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(request.user, nh, node, location_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_firewall.html',
                                      {'node_handle': nh, 'node': node, 'form': form, 'location': location,
                                       'owner_relationships': owner_relationships,
                                       'service_relationships': service_relationships},
                                      context_instance=RequestContext(request))
    else:
        form = forms.EditFirewallForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_firewall.html',
                                  {'node_handle': nh, 'node': node, 'form': form, 'location': location,
                                   'owner_relationships': owner_relationships,
                                   'service_relationships': service_relationships},
                                  context_instance=RequestContext(request))


@login_required
def edit_switch(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    location = h.iter2list(h.get_location(node))
    owner_relationships = h.iter2list(node.Owns.incoming)
    service_relationships = h.iter2list(node.Depends_on.incoming)
    ports = h.iter2list(h.get_ports(node))
    if request.POST:
        form = forms.EditSwitchForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Switch specific updates
            if form.cleaned_data['relationship_owner']:
                owner_id = form.cleaned_data['relationship_owner']
                node = h.set_owner(request.user, node, owner_id)
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(request.user, nh, node, location_id)
            if form.cleaned_data['relationship_ports']:
                for port in form.cleaned_data['relationship_ports']:
                    h.create_port(node, port, request.user)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_switch.html',
                                      {'node_handle': nh, 'node': node, 'form': form, 'location': location,
                                       'owner_relationships': owner_relationships, 'ports': ports,
                                       'service_relationships': service_relationships},
                                      context_instance=RequestContext(request))
    else:
        form = forms.EditSwitchForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_switch.html',
                                  {'node_handle': nh, 'node': node, 'form': form, 'location': location,
                                   'owner_relationships': owner_relationships, 'ports': ports,
                                   'service_relationships': service_relationships},
                                  context_instance=RequestContext(request))


@login_required        
def edit_router(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    location = h.iter2list(h.get_location(node))
    if request.POST:
        form = forms.EditRouterForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Router specific updates
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(request.user, nh, node, location_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_router.html',
                                  {'node': node, 'form': form, 
                                   'location': location},
                                context_instance=RequestContext(request))
    else:
        form = forms.EditRouterForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_router.html',
                                  {'node': node, 'form': form,
                                   'location': location},
                                context_instance=RequestContext(request)) 

@login_required
def edit_odf(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    location = h.iter2list(h.get_location(node))
    ports = h.iter2list(h.get_ports(node))
    if request.POST:
        form = forms.EditOdfForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # ODF specific updates
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(request.user, nh, node, location_id)
            if form.cleaned_data['relationship_ports']:
                for port in form.cleaned_data['relationship_ports']:
                    h.create_port(node, port, request.user)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_odf.html',
                                      {'node': node, 'form': form,
                                       'location': location, 'ports': ports},
                                      context_instance=RequestContext(request))
    else:
        form = forms.EditOdfForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_odf.html',
                                  {'node': node, 'form': form,
                                   'location': location, 'ports': ports},
                                  context_instance=RequestContext(request))


@login_required
def edit_external_equipment(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    owner_relationships = h.iter2list(node.Owns.incoming)
    location = h.iter2list(h.get_location(node))
    ports = h.iter2list(h.get_ports(node))
    if request.POST:
        form = forms.EditExternalEquipmentForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # External Equipment specific updates
            if form.cleaned_data['relationship_owner']:
                owner_id = form.cleaned_data['relationship_owner']
                node = h.set_owner(request.user, node, owner_id)
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(request.user, nh, node, location_id)
            if form.cleaned_data['relationship_ports']:
                for port in form.cleaned_data['relationship_ports']:
                    h.create_port(node, port, request.user)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_external_equipment.html',
                                      {'node': node, 'form': form, 'owner_relationships': owner_relationships,
                                       'location': location, 'ports': ports},
                                      context_instance=RequestContext(request))
    else:
        form = forms.EditExternalEquipmentForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_external_equipment.html',
                                  {'node': node, 'form': form, 'owner_relationships': owner_relationships,
                                   'location': location, 'ports': ports},
                                  context_instance=RequestContext(request))


@login_required
def edit_port(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    nh, node = h.get_nh_node(handle_id)
    location = h.iter2list(h.get_place(node))
    if request.POST:
        form = forms.EditPortForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Port specific updates
            if form.cleaned_data['relationship_parent']:
                parent_id = form.cleaned_data['relationship_parent']
                h.place_child_in_parent(request.user, node, parent_id)
            else:
                # Remove existing location if any
                for rel in h.iter2list(node.Located_in.outgoing):
                    nc.delete_relationship(nc.neo4jdb, rel)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_port.html',
                                     {'node': node, 'form': form, 'location': location},
                                     context_instance=RequestContext(request))
    else:
        form = forms.EditPortForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_port.html',
                                 {'form': form, 'node': node, 'location': location},
                                 context_instance=RequestContext(request))
@login_required
def edit_customer(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditCustomerForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_customer.html',
                    {'node': node, 'form': form},
                                      context_instance=RequestContext(request))
    else:
        form = forms.EditCustomerForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_customer.html',
                {'form': form, 'node': node},
                                  context_instance=RequestContext(request))

@login_required
def edit_end_user(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditEndUserForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_end_user.html',
                    {'node': node, 'form': form},
                                      context_instance=RequestContext(request))
    else:
        form = forms.EditEndUserForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_end_user.html',
                {'form': form, 'node': node},
                                  context_instance=RequestContext(request))

@login_required
def edit_provider(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditProviderForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_provider.html',
                    {'node': node, 'form': form},
                                      context_instance=RequestContext(request))
    else:
        form = forms.EditProviderForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_provider.html',
                {'form': form, 'node': node},
                                  context_instance=RequestContext(request))

@login_required
def edit_service(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    providers =  h.iter2list(node.Provides.incoming)
    customers = h.iter2list(h.get_customer(node))
    end_users = h.iter2list(h.get_end_user(node))
    depends_on = h.iter2list(h.get_logical_depends_on(node))
    if request.POST:
        form = forms.EditServiceForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Service node updates
            if form.cleaned_data['relationship_provider']:
                provider_id = form.cleaned_data['relationship_provider']
                h.set_provider(request.user, node, provider_id)
            if form.cleaned_data['relationship_customer']:
                customer_id = form.cleaned_data['relationship_customer']
                h.set_user(request.user, node, customer_id)
            if form.cleaned_data['relationship_end_user']:
                end_user_id = form.cleaned_data['relationship_end_user']
                h.set_user(request.user, node, end_user_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_id = form.cleaned_data['relationship_depends_on']
                h.set_depends_on(request.user, node, depends_on_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_service.html',
                                     {'form': form, 'node': node,
                                      'providers': providers, 'customers': customers,
                                      'end_users': end_users, 'depends_on': depends_on},
                                     context_instance=RequestContext(request))
    else:
        form = forms.EditServiceForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_service.html',
                                 {'form': form, 'node': node,
                                  'providers': providers, 'customers': customers,
                                  'end_users': end_users, 'depends_on': depends_on},
                                  context_instance=RequestContext(request))


@login_required
def edit_optical_link(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    providers = h.iter2list(node.Provides.incoming)
    depends_on = h.iter2list(h.get_logical_depends_on(node))
    if request.POST:
        form = forms.EditOpticalLinkForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Optical Link node updates
            if form.cleaned_data['relationship_provider']:
                provider_id = form.cleaned_data['relationship_provider']
                h.set_provider(request.user, node, provider_id)
            if form.cleaned_data['relationship_end_a']:
                depends_on_id = form.cleaned_data['relationship_end_a']
                h.set_depends_on(request.user, node, depends_on_id)
            if form.cleaned_data['relationship_end_b']:
                depends_on_id = form.cleaned_data['relationship_end_b']
                h.set_depends_on(request.user, node, depends_on_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_optical_link.html',
                {'form': form, 'node': node,
                 'providers': providers, 'depends_on': depends_on},
                context_instance=RequestContext(request))
    else:
        form = forms.EditOpticalLinkForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_optical_link.html',
            {'form': form, 'node': node,
             'providers': providers, 'depends_on': depends_on},
            context_instance=RequestContext(request))


@login_required
def edit_optical_multiplex_section(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    providers = h.iter2list(node.Provides.incoming)
    depends_on = h.iter2list(h.get_logical_depends_on(node))
    if request.POST:
        form = forms.EditOpticalMultiplexSectionForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Optical Multiplex Section node updates
            if form.cleaned_data['relationship_provider']:
                provider_id = form.cleaned_data['relationship_provider']
                h.set_provider(request.user, node, provider_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_id = form.cleaned_data['relationship_depends_on']
                h.set_depends_on(request.user, node, depends_on_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_optical_multiplex_section.html',
                                      {'form': form, 'node': node, 'providers': providers,
                                       'depends_on': depends_on}, context_instance=RequestContext(request))
    else:
        form = forms.EditOpticalMultiplexSectionForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_optical_multiplex_section.html',
                                  {'form': form, 'node': node, 'providers': providers,
                                   'depends_on': depends_on}, context_instance=RequestContext(request))


@login_required
def edit_optical_path(request, handle_id):
    if not request.user.is_staff:
        raise Http404
        # Get needed data from node
    nh, node = h.get_nh_node(handle_id)
    providers =  h.iter2list(node.Provides.incoming)
    depends_on = h.iter2list(h.get_logical_depends_on(node))
    if request.POST:
        form = forms.EditOpticalPathForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Optical Path node updates
            if form.cleaned_data['relationship_provider']:
                provider_id = form.cleaned_data['relationship_provider']
                h.set_provider(request.user, node, provider_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_id = form.cleaned_data['relationship_depends_on']
                h.set_depends_on(request.user, node, depends_on_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_optical_path.html',
                {'form': form, 'node': node,
                 'providers': providers, 'depends_on': depends_on},
                context_instance=RequestContext(request))
    else:
        form = forms.EditOpticalPathForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_optical_path.html',
            {'form': form, 'node': node,
             'providers': providers, 'depends_on': depends_on},
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
