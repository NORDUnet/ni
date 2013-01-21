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
    if nc.get_node_meta_type(node) == 'physical':
        # Remove dependant equipment like Ports
        for rel in node.Has.outgoing:
            child_nh, child_node = h.get_nh_node(rel.end['handle_id'])
            # Remove Units if any
            for rel2 in child_node.Depends_on.incoming:
                if rel2.start['node_type'] == 'Unit':
                    unit_nh, unit_node = h.get_nh_node(rel2.start['handle_id'])
                    unit_nh.delete()
            child_nh.delete()
    nh.delete()
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
        WHERE (parent-[:Has]->child or parent<-[:Located_in]-child or (parent<-[:Depends_on]-child and child.node_type = "Unit")) %s
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
                with nc.neo4jdb.transaction:
                    node['name'] = form.cleaned_data['name'].upper()

                    nh.node_name = node['name']
                    nh.save()
                # Update search index
                index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
                nc.update_index_item(nc.neo4jdb, index, node, 'name')
            if form.cleaned_data['country']:
                inverse_cm = dict((forms.COUNTRY_MAP[key], key) for key  in forms.COUNTRY_MAP)
                with nc.neo4jdb.transaction:
                    node['country_code'] = inverse_cm[node['country']]
            # Set site owner
            if form.cleaned_data['relationship_site_owner']:
                owner_id = form.cleaned_data['relationship_site_owner']
                owner_node = nc.get_node_by_id(nc.neo4jdb, owner_id)
                rel_exist = nc.get_relationships(node, owner_node, 
                                                     'Responsible_for')
                if not rel_exist:
                    try:
                        owner_rel = h.iter2list(node.Responsible_for.incoming)
                        with nc.neo4jdb.transaction:
                            owner_rel[0].delete()
                    except IndexError:
                        # No site owner set
                        pass
                    nc.create_relationship(nc.neo4jdb, owner_node,
                                                    node, 'Responsible_for')
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
                with nc.neo4jdb.transaction:
                    node['name'] = form.cleaned_data['telenor_trunk_id']
                    nh.node_name = form.cleaned_data['telenor_trunk_id']
                    nh.save()
            # Update search index for name
            index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
            nc.update_index_item(nc.neo4jdb, index, node, 'name')
            if form.cleaned_data['relationship_end_a']:
                end_a = form.cleaned_data['relationship_end_a']
                h.connect_physical(node, end_a)
            if form.cleaned_data['relationship_end_b']:
                end_b = form.cleaned_data['relationship_end_b']
                h.connect_physical(node, end_b)
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
    location = h.iter2list(h.get_location(node))
    if request.POST:
        form = forms.EditOpticalNodeForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Optical Node specific updates
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(nh, node, location_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_optical_node.html',
                                  {'node': node, 'form': form,
                                   'location': location},
                                context_instance=RequestContext(request))
    else:
        form = forms.EditOpticalNodeForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_optical_node.html',
                                  {'form': form, 'location': location,
                                   'node': node},
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
    if request.POST:
        form = forms.EditRackForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Rack specific updates
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                h.place_child_in_parent(node, location_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_rack.html',
                                  {'node': node, 'form': form,
                                   'location': location},
                                context_instance=RequestContext(request))
    else:
        form = forms.EditRackForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_rack.html',
                                  {'form': form, 'location': location,
                                   'node': node},
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
    if request.POST:
        form = forms.EditHostForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Host specific updates
            if form.cleaned_data['relationship_user']:
                user_id = form.cleaned_data['relationship_user']
                node = h.set_user(node, user_id)
            if form.cleaned_data['relationship_owner']:
                owner_id = form.cleaned_data['relationship_owner']
                node = h.set_owner(node, owner_id)
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(nh, node, location_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_host.html',
                                  {'node_handle': nh, 'node': node, 'form': form,
                                   'location': location, 'owner_relationships': owner_relationships,
                                   'user_relationships': user_relationships},
                                context_instance=RequestContext(request))
    else:
        form = forms.EditHostForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_host.html',
                                  {'node_handle': nh, 'node': node, 'form': form,
                                   'location': location, 'owner_relationships': owner_relationships,
                                   'user_relationships': user_relationships},
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
                nh, node = h.place_physical_in_location(nh, node, location_id)
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
    if request.POST:
        form = forms.EditOdfForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # ODF specific updates
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(nh, node, location_id)
            if 'saveanddone' in request.POST:
                return HttpResponseRedirect(nh.get_absolute_url())
            else:
                return HttpResponseRedirect('%sedit' % nh.get_absolute_url())
        else:
            return render_to_response('noclook/edit/edit_odf.html',
                                  {'node': node, 'form': form,
                                   'location': location},
                                context_instance=RequestContext(request))
    else:
        form = forms.EditOdfForm(h.item2dict(node))
        return render_to_response('noclook/edit/edit_odf.html',
                                  {'form': form, 'location': location,
                                   'node': node},
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
                h.place_child_in_parent(node, parent_id)
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
                h.set_provider(node, provider_id)
            if form.cleaned_data['relationship_customer']:
                customer_id = form.cleaned_data['relationship_customer']
                h.set_user(node, customer_id)
            if form.cleaned_data['relationship_end_user']:
                end_user_id = form.cleaned_data['relationship_end_user']
                h.set_user(node, end_user_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_id = form.cleaned_data['relationship_depends_on']
                h.set_depends_on(node, depends_on_id)
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
    providers =  h.iter2list(node.Provides.incoming)
    depends_on = h.iter2list(h.get_logical_depends_on(node))
    if request.POST:
        form = forms.EditOpticalLinkForm(request.POST)
        if form.is_valid():
            # Generic node update
            h.form_update_node(request.user, node, form)
            # Optical Link node updates
            if form.cleaned_data['relationship_provider']:
                provider_id = form.cleaned_data['relationship_provider']
                h.set_provider(node, provider_id)
            if form.cleaned_data['relationship_end_a']:
                depends_on_id = form.cleaned_data['relationship_end_a']
                h.set_depends_on(node, depends_on_id)
            if form.cleaned_data['relationship_end_b']:
                depends_on_id = form.cleaned_data['relationship_end_b']
                h.set_depends_on(node, depends_on_id)
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
                h.set_provider(node, provider_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_id = form.cleaned_data['relationship_depends_on']
                h.set_depends_on(node, depends_on_id)
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
    'service': edit_service,
    'host': edit_host,
    'odf': edit_odf,
    'optical-node': edit_optical_node,
    'optical-link': edit_optical_link,
    'optical-path': edit_optical_path,
    'peering-partner': edit_peering_partner,
    'port': edit_port,
    'provider': edit_provider,
    'rack': edit_rack,
    'router': edit_router,
    'site': edit_site,
    'site-owner': edit_site_owner,
}
