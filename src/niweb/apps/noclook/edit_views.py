# -*- coding: utf-8 -*-
"""
Created on Wed Dec 14 14:00:03 2011

@author: lundberg

Node manipulation views.
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.template import RequestContext
from django.template.defaultfilters import slugify
from niweb.apps.noclook.models import NodeHandle, NodeType
from niweb.apps.noclook.forms import NewSiteForm

import norduni_client as nc
import ipaddr
import json
from lucenequerybuilder import Q

COUNTRIES = {'DK': 'Denmark', 'FI': 'Finland', 'NL': 'Neatherlands',
             'NO': 'Norway', 'SE': 'Sweden', 'UK': 'United Kingdom', 
             'US': 'USA'}

@login_required
def new_node(request, slug=None):
    if not request.user.is_staff:
        raise Http404
    forms = {'site': NewSiteForm}
    if request.POST:
        form = forms[slug](request.POST)
        if form.is_valid():
            node_name = form.cleaned_data['name']
            node_type = get_object_or_404(NodeType, slug=slug)
            node_meta_type = request.POST['meta_type']
            node_handle = NodeHandle(node_name=node_name,
                                node_type=node_type,
                                node_meta_type=node_meta_type,
                                modifier=request.user, creator=request.user)
            node_handle.save()
            nc.set_noclook_auto_manage(nc.neo4jdb, node_handle.get_node(),
                                       False)
            # Type specific finishing
            type_func = {'Site': new_site}
            return type_func[str(node_type)](request, node_handle, form)
    if not slug:
        node_types = get_list_or_404(NodeType)
        return render_to_response('noclook/new_node.html', 
                              {'node_types': node_types})
    else:
        return render_to_response('noclook/create_%s.html' % slug, 
                                  {'form': forms[slug]},
                                context_instance=RequestContext(request))
                                
@login_required
def new_site(request, node_handle, form):
    node = node_handle.get_node()
    with nc.neo4jdb.transaction:
        node['name'] = form.cleaned_data['name'].upper()
        keys = ['country_code', 'address', 'postarea', 'postcode']
        for key in keys:
            node[key] = form.cleaned_data[key]
        node['country'] = COUNTRIES[node['country_code']]
    return HttpResponseRedirect('/site/%d' % node_handle.handle_id)

@login_required
def edit_node(request, slug):
    if not request.user.is_staff:
        raise Http404
    if request.POST:
        nh = get_object_or_404(NodeHandle, pk=handle_id)
    else:
        return render_to_response('noclook/edit_%s.html' % slug,
                                  {'form': forms[slug]},
                                context_instance=RequestContext(request))

@login_required
def save_node(request):
    if not request.user.is_staff:
        raise Http404 
    if request.POST:
        pass

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
#    '''
#    View used to change and add properties to a node, also to delete
#    a node relationships.
#    '''
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
#    '''
#    Updates the node and node_handle with new values.
#    '''
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
#    '''
#    Deletes the NodeHandle from the SQL database and the node from the Neo4j
#    database.
#    '''    
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
#    '''
#    Create a new relationship between the node that was edited and another node.
#    
#    The way to get the nodes that are suitible for relationships have to be
#    tought over again. This way is pretty hary.
#    '''
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
#    '''
#    View to update, change or delete relationships properties.
#    '''
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
#    '''
#    Deletes the relationship if POST['confirmed']==True.
#    '''
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
