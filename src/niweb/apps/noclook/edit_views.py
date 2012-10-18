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
def get_nh_node(node_handle_id):
    """
    Takes a node handle id and returns the node handle and the node.
    """
    nh = get_object_or_404(NodeHandle, pk=node_handle_id)
    node = nh.get_node()
    return nh, node
    
def slug_to_node_type(slug, create=False):
    """
    Returns or creates and returns the NodeType object from the supplied slug.
    """
    acronym_types = ['odf'] # TODO: Move to sql db
    if create:
        node_type, created = NodeType.objects.get_or_create(slug=slug)
        if created:
            if slug in acronym_types:
                type_name = slug.upper()
            else:
                type_name = slug.replace('-', ' ').title()
            node_type.type = type_name
            node_type.save()
    else:
        node_type = get_object_or_404(NodeType, slug=slug)
    return node_type

def form_update_node(user, node, form, property_keys=None):
    """
    Take a node, a form and the property keys that should be used to fill the
    node if the property keys are omitted the form.base_fields will be used.
    Returns True if all non-empty properties where added else False and 
    rollbacks the node changes.
    """
    if not property_keys:
        property_keys = []
    meta_fields = ['relationship_location', 'relationship_end_a',
                   'relationship_end_b', 'relationship_parent',
                   'relationship_provider', 'relationship_end_user',
                   'relationship_customer', 'relationship_depends_on']
    nh = get_object_or_404(NodeHandle, pk=node['handle_id'])
    if not property_keys:
        for field in form.base_fields.keys():
            if field not in meta_fields:
                property_keys.append(field)
    for key in property_keys:
        try:
            if form.cleaned_data[key] or form.cleaned_data[key] == 0:
                pre_value = node.getProperty(key, '')
                if pre_value != form.cleaned_data[key]:
                    with nc.neo4jdb.transaction:
                        node[key] = form.cleaned_data[key]
                    if key == 'name':
                        nh.node_name = form.cleaned_data[key]
                    nh.modifier = user
                    nh.save()
                    h.update_node_search_index(nc.neo4jdb, node)
            elif not form.cleaned_data[key] and key != 'name':
                with nc.neo4jdb.transaction:
                    del node[key]
                if key in django_settings.SEARCH_INDEX_KEYS:
                    index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
                    nc.del_index_item(nc.neo4jdb, index, key)
        except KeyError:
            return False
        except Exception:
            # If the property type differs from what is allowed in node 
            # properties. Force string as last alternative.
            with nc.neo4jdb.transaction:
                node[key] = unicode(form.cleaned_data[key])
    return True



@login_required
def delete_node(request, slug, handle_id):
    """
    Removes the node and all relationships to and from that node.
    """
    nh, node = get_nh_node(handle_id)
    if nc.get_node_meta_type(node) == 'physical':
        # Remove dependant equipment like Ports
        for rel in node.Has.outgoing:
            child_nh, child_node = get_nh_node(rel.end['handle_id'])
            # Remove Units if any
            for rel2 in child_node.Depends_on.incoming:
                if rel2.start['node_type'] == 'Unit':
                    unit_nh, unit_node = get_nh_node(rel2.start['handle_id'])
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
    nh, node = get_nh_node(handle_id)
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
    node_type = slug_to_node_type(slug)
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
        type_filter = 'and child.node_type = "%s"' % slug_to_node_type(slug)
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

def form_to_generic_node_handle(request, form, slug, node_meta_type):
    node_name = form.cleaned_data['name']
    node_type = slug_to_node_type(slug, create=True)
    node_handle = NodeHandle(node_name=node_name,
                             node_type=node_type,
                             node_meta_type=node_meta_type,
                             modifier=request.user, creator=request.user)
    node_handle.save()
    h.set_noclook_auto_manage(nc.neo4jdb, node_handle.get_node(),
                              False)
    return node_handle

def form_to_unique_node_handle(request, form, slug, node_meta_type):
    node_name = form.cleaned_data['name']
    node_type = slug_to_node_type(slug, create=True)
    try:
        node_handle = NodeHandle.objects.get(node_name=node_name, node_type=node_type)
        raise UniqueNodeError(node_handle.get_node())
    except NodeHandle.DoesNotExist:
        node_handle = NodeHandle.objects.create(node_name=node_name,
                                                node_type=node_type,
                                                node_meta_type=node_meta_type,
                                                modifier=request.user,
                                                creator=request.user)
        h.set_noclook_auto_manage(nc.neo4jdb, node_handle.get_node(), False)
    return node_handle

# Reserve Ids
@login_required
def reserve_id(request, slug=None):
    if not slug:
        return render_to_response('noclook/edit/reserve_id.html', {},
                                  context_instance=RequestContext(request))
    if request.POST:
        form = forms.ReserveIdForm(request.POST)
        if form.is_valid():
            reserved_list = h.reserve_nordunet_id(slug, form.cleaned_data['amount'],
                form.cleaned_data['reserve_message'], request.user)
            return render_to_response('noclook/edit/reserve_id.html', {'reserved_list': reserved_list, 'slug': slug},
                context_instance=RequestContext(request))
        else:
            return render_to_response('noclook/edit/reserve_id.html', {'form': form, 'slug': slug},
                                      context_instance=RequestContext(request))
    else:
        form = forms.ReserveIdForm()
        return render_to_response('noclook/edit/reserve_id.html', {'form': form, 'slug': slug},
                                  context_instance=RequestContext(request))

# Create functions
@login_required
def new_node(request, slug=None, **kwargs):
    """
    Generic create function that redirects calls to node type sensitive create functions.
    """
    if not request.user.is_staff:
        raise Http404
    # Template name is create_type_slug.html.
    template = 'noclook/edit/create_%s.html' % slug
    template = template.replace('-', '_')
    if request.POST:
        form = NEW_FORMS[slug](request.POST)
        if form.is_valid():
            try:
                func = NEW_FUNC[slug]
            except KeyError:
                raise Http404
            return func(request, form, **kwargs)
        else:
            return render_to_response(template, {'form': form},
                                context_instance=RequestContext(request))
    if not slug:
        return render_to_response('noclook/edit/new_node.html', {},
                                  context_instance=RequestContext(request))
    else:
        try:
            form = NEW_FORMS[slug]
            if kwargs.get('name', None):
                form = form(initial={'name': kwargs['name']})
        except KeyError:
            raise Http404
        return render_to_response(template, {'form': form},
                                  context_instance=RequestContext(request))

@login_required
def new_site(request, form):
    try:
        nh = form_to_unique_node_handle(request, form, 'site', 'location')
    except UniqueNodeError:
        form = forms.NewSiteForm(request.POST)
        form._errors = ErrorDict()
        form._errors['name'] = ErrorList()
        form._errors['name'].append('A Site with that name already exists.')
        return render_to_response('noclook/edit/create_site.html', {'form': form},
                                  context_instance=RequestContext(request))
    node = nh.get_node()
    keys = ['country_code', 'address', 'postarea', 'postcode']
    form_update_node(request.user, node, form, keys)
    with nc.neo4jdb.transaction:
        node['name'] = '%s-%s' % (form.cleaned_data['country_code'], form.cleaned_data['name'].upper())
        node['country'] = forms.COUNTRY_MAP[node['country_code']]
        nh.node_name = node['name']
        nh.save()
    # Update search index
    index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
    nc.update_index_item(nc.neo4jdb, index, node, 'name')
    return HttpResponseRedirect(nh.get_absolute_url())
    
@login_required
def new_site_owner(request, form):
    try:
        nh = form_to_unique_node_handle(request, form, 'site-owner', 'relation')
    except UniqueNodeError:
        form = forms.NewSiteOwnerForm(request.POST)
        form._errors = ErrorDict()
        form._errors['name'] = ErrorList()
        form._errors['name'].append('A Site Owner with that name already exists.')
        return render_to_response('noclook/edit/create_site_owner.html', {'form': form},
                                  context_instance=RequestContext(request))
    node = nh.get_node()
    keys = ['url']
    form_update_node(request.user, node, form, keys)
    return HttpResponseRedirect(nh.get_absolute_url())
    
@login_required
def new_cable(request, form, **kwargs):
    try:
        nh = form_to_unique_node_handle(request, form, 'cable', 'physical')
    except UniqueNodeError:
        form = forms.NewCableForm(request.POST)
        form._errors = ErrorDict()
        form._errors['name'] = ErrorList()
        form._errors['name'].append('A Cable with that name already exists.')
        return render_to_response('noclook/edit/create_cable.html', {'form': form},
                                  context_instance=RequestContext(request))
    node = nh.get_node()
    keys = ['cable_type']
    form_update_node(request.user, node, form, keys)
    return HttpResponseRedirect(nh.get_absolute_url())

@login_required
def new_rack(request, form):
    nh = form_to_generic_node_handle(request, form, 'rack', 'location')
    node = nh.get_node()
    form_update_node(request.user, node, form)
    if form.cleaned_data['relationship_location']:
        location_id = form.cleaned_data['relationship_location']
        location_node = nc.get_node_by_id(nc.neo4jdb,  location_id)
        rel_exist = nc.get_relationships(location_node, node, 'Has')
        if not rel_exist:
            try:
                location_rel = h.iter2list(node.Has.incoming)
                with nc.neo4jdb.transaction:
                    location_rel[0].delete()
            except IndexError:
                # No site set
                pass
            nc.create_relationship(nc.neo4jdb, location_node, node, 'Has')
    return HttpResponseRedirect(nh.get_absolute_url())

@login_required        
def new_odf(request, form):
    nh = form_to_generic_node_handle(request, form, 'odf', 'physical')
    node = nh.get_node()
    form_update_node(request.user, node, form)
    return HttpResponseRedirect(nh.get_absolute_url())

@login_required
def new_port(request, form, parent_id=None):
    nh = form_to_generic_node_handle(request, form, 'port', 'physical')
    node = nh.get_node()
    keys = ['port_type']
    form_update_node(request.user, node, form, keys)
    if parent_id:
        try:
            h.place_child_in_parent(node, parent_id)
        except NoRelationshipPossible:
            nh.delete()
            form = forms.NewSiteForm(request.POST)
            form._errors = ErrorDict()
            form._errors['parent'] = ErrorList()
            form._errors['parent'].append('Parent type can not have ports.')
            return render_to_response('noclook/edit/create_port.html', {'form': form},
                context_instance=RequestContext(request))
    return HttpResponseRedirect(nh.get_absolute_url())

@login_required
def new_customer(request, form):
    try:
        nh = form_to_unique_node_handle(request, form, 'customer', 'relation')
    except UniqueNodeError:
        form = forms.NewCustomerForm(request.POST)
        form._errors = ErrorDict()
        form._errors['name'] = ErrorList()
        form._errors['name'].append('A Customer with that name already exists.')
        return render_to_response('noclook/edit/create_customer.html', {'form': form},
                                  context_instance=RequestContext(request))
    node = nh.get_node()
    keys = ['url']
    form_update_node(request.user, node, form, keys)
    return HttpResponseRedirect(nh.get_absolute_url())

@login_required
def new_end_user(request, form):
    try:
        nh = form_to_unique_node_handle(request, form, 'end-user', 'relation')
    except UniqueNodeError:
        form = forms.NewEndUserForm(request.POST)
        form._errors = ErrorDict()
        form._errors['name'] = ErrorList()
        form._errors['name'].append('An End User with that name already exists.')
        return render_to_response('noclook/edit/create_end_user.html', {'form': form},
                                  context_instance=RequestContext(request))
    node = nh.get_node()
    keys = ['url']
    form_update_node(request.user, node, form, keys)
    return HttpResponseRedirect(nh.get_absolute_url())

@login_required
def new_provider(request, form):
    try:
        nh = form_to_unique_node_handle(request, form, 'provider', 'relation')
    except UniqueNodeError:
        form = forms.NewProviderForm(request.POST)
        form._errors = ErrorDict()
        form._errors['name'] = ErrorList()
        form._errors['name'].append('A Provider with that name already exists.')
        return render_to_response('noclook/edit/create_provider.html', {'form': form},
                                  context_instance=RequestContext(request))
    node = nh.get_node()
    keys = ['url']
    form_update_node(request.user, node, form, keys)
    return HttpResponseRedirect(nh.get_absolute_url())

@login_required
def new_nordunet_service(request, form):
    try:
        nh = form_to_unique_node_handle(request, form, 'service', 'logical')
    except UniqueNodeError:
        form = forms.NewServiceForm(request.POST)
        form._errors = ErrorDict()
        form._errors['name'] = ErrorList()
        form._errors['name'].append('A Service with that name already exists.')
        return render_to_response('noclook/edit/create_nordunet_service.html', {'form': form},
                                  context_instance=RequestContext(request))
    node = nh.get_node()
    keys = ['description', 'service_class', 'service_type', 'operational_state', 'project_end_date']
    form_update_node(request.user, node, form, keys)
    return HttpResponseRedirect(nh.get_absolute_url())

@login_required
def new_nordunet_optical_link(request, form):
    try:
        nh = form_to_unique_node_handle(request, form, 'optical-link', 'logical')
    except UniqueNodeError:
        form = forms.NewServiceForm(request.POST)
        form._errors = ErrorDict()
        form._errors['name'] = ErrorList()
        form._errors['name'].append('An Optical Link with that name already exists.')
        return render_to_response('noclook/edit/create_nordunet_optical_link.html', {'form': form},
            context_instance=RequestContext(request))
    node = nh.get_node()
    keys = ['description', 'link_type', 'operational_state', 'inteface_type']
    form_update_node(request.user, node, form, keys)
    return HttpResponseRedirect(nh.get_absolute_url())

@login_required
def new_nordunet_optical_path(request, form):
    try:
        nh = form_to_unique_node_handle(request, form, 'optical-path', 'logical')
    except UniqueNodeError:
        form = forms.NewServiceForm(request.POST)
        form._errors = ErrorDict()
        form._errors['name'] = ErrorList()
        form._errors['name'].append('An Optical Path with that name already exists.')
        return render_to_response('noclook/edit/create_nordunet_optical_path.html', {'form': form},
            context_instance=RequestContext(request))
    node = nh.get_node()
    keys = ['description', 'framing', 'capacity', 'operational_state']
    form_update_node(request.user, node, form, keys)
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
def edit_site(request, handle_id):
    if not request.user.is_staff:
        raise Http404
    # Get needed data from node
    nh, node = get_nh_node(handle_id)
    site_owner = h.iter2list(node.Responsible_for.incoming)
    if request.POST:
        form = forms.EditSiteForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
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
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    if request.POST:
        form = forms.EditSiteOwnerForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    connections = h.get_connected_cables(node)
    if request.POST:
        form = forms.EditCableForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
            # Cable specific update
            if form.cleaned_data['telenor_trunk_id']:
                with nc.neo4jdb.transaction:
                    node['name'] = form.cleaned_data['telenor_trunk_id']
                    nh.node_name = form.cleaned_data['telenor_trunk_id']
                    nh.save()
                # Update search index
                index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
                nc.update_index_item(nc.neo4jdb, index, node['name'], 'name')
            if form.cleaned_data['relationship_end_a']:
                end_a = form.cleaned_data['relationship_end_a']
                h.connect_physical(node, end_a)
            if form.cleaned_data['relationship_end_b']:
                end_b = form.cleaned_data['relationship_end_b']
                h.connect_physical(node, end_b)
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    location = h.iter2list(h.get_location(node))
    if request.POST:
        form = forms.EditOpticalNodeForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
            # Optical Node specific updates
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(nh, node, location_id)
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    if request.POST:
        form = forms.EditPeeringPartnerForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    location = h.iter2list(h.get_place(node))
    if request.POST:
        form = forms.EditRackForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
            # Rack specific updates
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                h.place_child_in_parent(node, location_id)
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    location = h.iter2list(h.get_location(node))
    owner_relationships = h.iter2list(node.Owns.incoming)    # Physical hosts
    user_relationships = h.iter2list(node.Uses.incoming)     # Logical hosts
    if request.POST:
        form = forms.EditHostForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
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
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    location = h.iter2list(h.get_location(node))
    if request.POST:
        form = forms.EditRouterForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
            # Router specific updates
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(nh, node, location_id)
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    location = h.iter2list(h.get_location(node))
    if request.POST:
        form = forms.EditOdfForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
            # ODF specific updates
            if form.cleaned_data['relationship_location']:
                location_id = form.cleaned_data['relationship_location']
                nh, node = h.place_physical_in_location(nh, node, location_id)
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    location = h.iter2list(h.get_place(node))
    if request.POST:
        form = forms.EditPortForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
            # Port specific updates
            if form.cleaned_data['relationship_parent']:
                parent_id = form.cleaned_data['relationship_parent']
                h.place_child_in_parent(node, parent_id)
            else:
                # Remove existing location if any
                for rel in h.iter2list(node.Located_in.outgoing):
                    nc.delete_relationship(nc.neo4jdb, rel)
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    if request.POST:
        form = forms.EditCustomerForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    if request.POST:
        form = forms.EditEndUserForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    if request.POST:
        form = forms.EditProviderForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    providers =  h.iter2list(node.Provides.incoming)
    customers = h.iter2list(h.get_customer(node))
    end_users = h.iter2list(h.get_end_user(node))
    depends_on = h.iter2list(h.get_logical_depends_on(node))
    if request.POST:
        form = forms.EditServiceForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
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
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    providers =  h.iter2list(node.Provides.incoming)
    depends_on = h.iter2list(h.get_logical_depends_on(node))
    if request.POST:
        form = forms.EditOpticalLinkForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
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
            return HttpResponseRedirect(nh.get_absolute_url())
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
    nh, node = get_nh_node(handle_id)
    providers =  h.iter2list(node.Provides.incoming)
    depends_on = h.iter2list(h.get_logical_depends_on(node))
    if request.POST:
        form = forms.EditOpticalPathForm(request.POST)
        if form.is_valid():
            # Generic node update
            form_update_node(request.user, node, form)
            # Optical Path node updates
            if form.cleaned_data['relationship_provider']:
                provider_id = form.cleaned_data['relationship_provider']
                h.set_provider(node, provider_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_id = form.cleaned_data['relationship_depends_on']
                h.set_depends_on(node, depends_on_id)
            return HttpResponseRedirect(nh.get_absolute_url())
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

NEW_FORMS =  {'cable': forms.NewCableForm,
              'customer': forms.NewCustomerForm,
              'end-user': forms.NewEndUserForm,
              'nordunet-optical-link': forms.NewNordunetOpticalLinkForm,
              'nordunet-optical-path': forms.NewNordunetOpticalPathForm,
              'nordunet-service': forms.NewNordunetServiceForm,
              'odf': forms.NewOdfForm,
              'port': forms.NewPortForm,
              'provider': forms.NewProviderForm,
              'rack': forms.NewRackForm,
              'site': forms.NewSiteForm, 
              'site-owner': forms.NewSiteOwnerForm,
             }

NEW_FUNC = {'cable': new_cable,
            'customer': new_customer,
            'end-user': new_end_user,
            'nordunet-optical-link': new_nordunet_optical_link,
            'nordunet-optical-path': new_nordunet_optical_path,
            'nordunet-service': new_nordunet_service,
            'odf': new_odf,
            'port': new_port,
            'provider': new_provider,
            'rack': new_rack,
            'site': new_site,
            'site-owner': new_site_owner,
            }

EDIT_FUNC = {'cable': edit_cable,
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

#@login_required
#def new_node_old(request):
#    if not request.user.is_staff:
#        raise Http404    
#    if request.POST:
#        # Create the new node
#        node_name = request.POST['name']
#        node_type = get_object_or_404(NodeType, slug=request.POST['node_types'])
#        node_meta_type = request.POST['meta_types'].lower()
#        node_handle = NodeHandle(node_name=node_name,
#                                node_type=node_type,
#                                node_meta_type=node_meta_type,
#                                modifier=request.user, creator=request.user)
#        node_handle.save()
#        nc.set_noclook_auto_manage(nc.neo4jdb, node_handle.get_node(), False)
#        return edit_node(request, slugify(node_handle.node_type), 
#                                                         node_handle.handle_id)
#    else:
#        node_types = get_list_or_404(NodeType)
#
#    return render_to_response('noclook/new_node2.html',
#                            {'node_types': node_types},
#                            context_instance=RequestContext(request))
#
#@login_required
#def edit_node_old(request, slug, handle_id, node=None, message=None):
#    """
#    View used to change and add properties to a node, also to delete
#    a node relationships.
#    """
#    if not request.user.is_staff:
#        raise Http404
#    nh = get_object_or_404(NodeHandle, pk=handle_id)
#    if not node:
#        node = nh.get_node()
#    # Make a dict of properties you want to be able to change
#    node_properties = {}
#    unwanted_properties = ['handle_id', 'node_type', 'noclook_auto_manage',
#                           'noclook_last_seen']
#    for key, value in node.items():
#        if key not in unwanted_properties:
#            try:
#                node_properties[key] = json.dumps(value)
#            except ValueError:
#                node_properties[key] = value
#    # Relationships
#    # Make a dict of relationships you want to be able to change
#    unwanted_relationships = ['Contains', 'Consist_of']
#    node_relationships = []
#    for rel in node.relationships:
#        relationship = {'properties': {}}
#        if rel.type.name() not in unwanted_relationships:
#            relationship['id'] = rel.id
#            relationship['start'] = rel.start['name']
#            relationship['type'] = rel.type.name()
#            relationship['end'] = rel.end['name']
#            for key in rel.getPropertyKeys():
#                if key not in unwanted_properties:
#                    relationship[key] = rel[key]
#            node_relationships.append(relationship)
#    return render_to_response('noclook/edit_node.html',
#                            {'node_handle': nh, 'node': node,
#                            'node_properties': node_properties,
#                            'node_relationships': node_relationships,
#                            'message': message},
#                            context_instance=RequestContext(request))
#
#@login_required
#def save_node_old(request, slug, handle_id):
#    """
#    Updates the node and node_handle with new values.
#    """
#    if not request.user.is_staff:
#        raise Http404
#    nh = get_object_or_404(NodeHandle, pk=handle_id)
#    node = nh.get_node()
#    if request.POST:
#        # request.POST is immutable.
#        post = request.POST.copy()
#        new_properties = {}
#        del post['csrfmiddlewaretoken']
#        # Add all new properties
#        for i in range(0, len(post)):
#            # To make this work we need js in the template to add new
#            # input with name new_keyN and new_valueN.
#            nk = 'new_key%d' % i
#            nv = 'new_value%d' % i
#            if (nk in post) and (nv in post):
#                #QueryDicts uses lists a values
#                new_properties[post[nk]] = post.get(nv)
#                del post[nk]
#                del post[nv]
#        # Add the remaining properties
#        for item in post:
#            new_properties[item] = post.get(item)
#        # Update the node
#        node = nc.update_item_properties(nc.neo4jdb, node, new_properties)
#        # Update the node_handle
#        nh.node_name = node['name']
#        nh.modifier = request.user
#        nc.update_noclook_auto_manage(nc.neo4jdb, node)
#        nh.save()
#    return edit_node(request, slug, handle_id, node=node)
#    
#@login_required
#def delete_node_old(request, slug, handle_id):
#    """
#    Deletes the NodeHandle from the SQL database and the node from the Neo4j
#    database.
#    """
#    if not request.user.is_staff:
#        raise Http404
#    if request.POST:
#        if 'confirmed' in request.POST and \
#                                        request.POST['confirmed'] == 'delete':
#            nh = get_object_or_404(NodeHandle, pk=handle_id)
#            nh.delete()
#            return HttpResponseRedirect('/%s/' % slug) 
#    return edit_node(request, slug, handle_id)
#
#@login_required
#def new_relationship_old(request, slug, handle_id):
#    """
#    Create a new relationship between the node that was edited and another node.
#    
#    The way to get the nodes that are suitible for relationships have to be
#    tought over again. This way is pretty hary.
#    """
#    if not request.user.is_staff:
#        raise Http404
#    nh = get_object_or_404(NodeHandle, pk=handle_id)
#    node = nh.get_node()
#    message = ''
#    if request.POST:
#        if request.POST['direction']:
#            direction = request.POST['direction']
#            node_id = request.POST['nodes']
#            other_node = nc.get_node_by_id(nc.neo4jdb, node_id)
#            rel_type = request.POST['types']
#            if direction == 'out':
#                rel = nc.create_suitable_relationship(nc.neo4jdb, node,
#                                                      other_node, rel_type)
#            else:
#                rel = nc.create_suitable_relationship(nc.neo4jdb, other_node,
#                                                      node, rel_type)
#            if rel:
#                nc.set_noclook_auto_manage(nc.neo4jdb, rel, False)
#                return edit_relationship(request, slug, handle_id, rel.id, rel)
#            else:
#                message = 'The requested relationship could not be made.' 
#        else:
#            message = 'You have to choose relationship direction.'
#    node_dicts = []
#    suitable_nodes = nc.get_suitable_nodes(nc.neo4jdb, node)
#    for item in ['physical', 'logical', 'relation', 'location']:
#        for n in suitable_nodes[item]:
#            parent = nc.get_root_parent(nc.neo4jdb, n)
#            if parent:
#                name = '%s %s' % (parent['name'], n['name'])      
#            else:
#                name = n['name']
#                node_type = n['node_type']
#            node_dicts.append({'name': name, 
#                               'id':n.id, 
#                               'node_type': node_type})
#    return render_to_response('noclook/new_relationship.html',
#                            {'node_handle': nh, 'node': node, 
#                             'node_dicts': node_dicts, 'message': message},
#                            context_instance=RequestContext(request))
#
#@login_required
#def edit_relationship_old(request, slug, handle_id, rel_id, rel=None, message=None):
#    """
#    View to update, change or delete relationships properties.
#    """
#    if not request.user.is_staff:
#        raise Http404
#    nh = get_object_or_404(NodeHandle, pk=handle_id)
#    if not rel:
#        rel = nc.get_relationship_by_id(nc.neo4jdb, rel_id)
#    rel_properties = {}
#    for key in rel.getPropertyKeys():
#        rel_properties[key] = rel[key]
#    return render_to_response('noclook/edit_relationship.html',
#                            {'node_handle': nh, 'rel': rel, 
#                             'rel_properties': rel_properties, 
#                             'message': message},
#                            context_instance=RequestContext(request))
#
#@login_required
#def save_relationship_old(request, slug, handle_id, rel_id):
#    if not request.user.is_staff:
#        raise Http404
#    rel = nc.get_relationship_by_id(nc.neo4jdb, rel_id)
#    if request.POST:
#        # request.POST is immutable.
#        post = request.POST.copy()
#        new_properties = {}
#        del post['csrfmiddlewaretoken']
#        # Add all new properties
#        for i in range(0, len(post)):
#            # To make this work we need js in the template to add new
#            # input with name new_keyN and new_valueN.
#            nk = 'new_key%d' % i
#            nv = 'new_value%d' % i
#            if (nk in post) and (nv in post):
#                #QueryDicts uses lists a values
#                new_properties[post[nk]] = post.get(nv)
#                del post[nk]
#                del post[nv]
#        # Add the remaining properties
#        for item in post:
#            new_properties[item] = post.get(item)
#        # Update the relationships properties
#        rel = nc.update_item_properties(nc.neo4jdb, rel, new_properties)
#        nc.update_noclook_auto_manage(nc.neo4jdb, rel)
#    return edit_relationship(request, slug, handle_id, rel_id, rel)
#
#@login_required
#def delete_relationship_old(request, slug, handle_id, rel_id):
#    """
#    Deletes the relationship if POST['confirmed']==True.
#    """
#    if not request.user.is_staff or not request.POST:
#        raise Http404
#    if 'confirmed' in request.POST.keys():
#        nh = get_object_or_404(NodeHandle, pk=handle_id)
#        node = nh.get_node()
#        message = 'No relationship matching the query was found. Nothing deleted.'
#        for rel in node.relationships:
#            cur_id = str(rel.id)
#            if cur_id == rel_id and cur_id in request.POST['confirmed']:
#                message = 'Relationship %s %s %s deleted.' % (rel.start['name'],
#                                                              rel.type,
#                                                              rel.end['name']) 
#                with nc.neo4jdb.transaction:
#                    rel.delete()
#                break                
#        return edit_node(request, slug, handle_id, message=message)
#    else:            
#        message = 'Please confirm the deletion of the relationship.'
#        return edit_node(request, slug, handle_id, message=message)
