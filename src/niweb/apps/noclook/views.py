# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.template import RequestContext
from django.template.defaultfilters import slugify
from niweb.apps.noclook.models import NodeHandle, NodeType

import norduni_client as nc
import ipaddr
import json
from lucenequerybuilder import Q

def index(request):
    return render_to_response('noclook/index.html', {},
        context_instance=RequestContext(request))

@login_required
def logout_page(request):
    '''
    Log users out and redirects them to the index.
    '''
    logout(request)
    return HttpResponseRedirect('/')

# List views
@login_required
def list_by_type(request, slug):
    node_type = get_object_or_404(NodeType, slug=slug)
    node_handle_list = node_type.nodehandle_set.all()
    return render_to_response('noclook/list_by_type.html',
        {'node_handle_list': node_handle_list, 'node_type': node_type},
        context_instance=RequestContext(request))
        
@login_required
def list_peering_partners(request):
    node_types_index = nc.get_node_index(nc.neo4jdb, 'node_types')
    q = Q('node_type', 'Peering Partner')
    hits = node_types_index.query('%s' % q)
    partner_list = []
    for node in hits:
        partner = {}
        partner['name'] = node['name']
        partner['as_number'] = node['as_number']
        partner['peering_partner'] = node
        partner_list.append(partner)
    return render_to_response('noclook/list_peering_partners.html',
                                {'partner_list': partner_list},
                                context_instance=RequestContext(request))

@login_required
def list_hosts(request):
    node_types_index = nc.get_node_index(nc.neo4jdb, 'node_types')
    q = Q('node_type', 'Host')
    hits = node_types_index.query('%s' % q)
    host_list = []
    for node in hits:
        try:
            addresses = node['addresses']
        except KeyError:
            addresses = []
        for address in addresses:
            host = {}
            host['name'] = node['name']
            host['address'] = address
            host['host'] = node
            host_list.append(host)
    return render_to_response('noclook/list_hosts.html',
                                {'host_list': host_list},
                                context_instance=RequestContext(request))
# Remove?
#@login_required
#def list_by_master(request, handle_id, slug):
#    nh = get_object_or_404(NodeHandle, pk=handle_id)
#    # Get node from neo4j-database
#    master = nh.get_node()
#    # Get all outgoing related nodes
#    node_list = master.traverse()
#    node_handle_list = []
#    node_type = get_object_or_404(NodeType, slug=slug)
#    for node in node_list:
#        if node['node_type'] == str(node_type):
#            node_handle_list.append(get_object_or_404(NodeHandle,
#                                        pk=node['handle_id']))
#    return render_to_response('noclook/list_by_type.html',
#        {'node_handle_list': node_handle_list},
#        context_instance=RequestContext(request))

# Detail views
@login_required
def generic_detail(request, handle_id, slug):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    return render_to_response('noclook/detail.html',
        {'node_handle': nh, 'node': node},
        context_instance=RequestContext(request))

@login_required
def router_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = nc.neo4j_data_age(node)
    # Get all the PICs and the PICs services. Also get loopback addresses.
    loopback_addresses = []
    pics = []
    for rel in node.Has.outgoing:
        pic = {'pic': rel.end , 'services': []}
        dep_units = pic['pic'].Depends_on.incoming
        for dep_unit in dep_units:
            unit = dep_unit.start
            if pic['pic']['name'] == 'lo0':
                loopback_addresses.extend(unit['ip_addresses'])
            dep_services = unit.Depends_on.incoming
            for service in dep_services:
                pic['services'].append(service.start)
        pics.append(pic)
    location_relationships = node.Located_in.outgoing
    for address in loopback_addresses:
        try:
            ipaddr.IPNetwork(address)
        except ValueError:
            # Remove the ISO address
            loopback_addresses.remove(address)
    return render_to_response('noclook/router_detail.html',
        {'node_handle': nh, 'node': node, 'pics': pics, 'last_seen': last_seen,
        'expired': expired, 'location_relationships': location_relationships,
        'loopback_addresses': loopback_addresses},
        context_instance=RequestContext(request))

@login_required
def pic_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = nc.neo4j_data_age(node)
    # Get the top parent node
    router = nc.get_root_parent(nc.neo4jdb, node)
    # Get unit nodes
    units = []
    depending_services = []
    dep_units = node.Depends_on.incoming
    for dep_unit in dep_units:
        unit = dep_unit.start            
        units.append(unit)
        dep_services = unit.Depends_on.incoming
        for dep_service in dep_services:
            address = dep_service['ip_address']
            service = {}
            service['if_address'] = address
            service['service'] = dep_service.start
            service['unit'] = unit 
            service['relations'] = []
            if_address = ipaddr.IPNetwork(address)
            # Get relations who uses the pic
            relation_rels = dep_service.start.Uses.incoming
            for r_rel in relation_rels:
                rel_address = ipaddr.IPAddress(r_rel['ip_address'])
                if rel_address in if_address:
                    relation = {'rel_address': r_rel['ip_address'],
                                'relation': r_rel.start}
                    service['relations'].append(relation)
            depending_services.append(service)    
    return render_to_response('noclook/pic_detail.html',
        {'node_handle': nh, 'node': node, 'router': router, 
         'last_seen': last_seen, 'expired': expired, 'units': units,
         'depending_services': depending_services}, 
         context_instance=RequestContext(request))

@login_required
def optical_node_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = nc.neo4j_data_age(node)
    #get incoming rels of fibers
    connected_rel = node.Connected_to.incoming
    opt_info = []
    for rel in connected_rel:
        fibers = {}
        fiber = rel.start
        fibers['fiber_name'] = fiber['name']
        fibers['fiber_url'] = nc.get_node_url(fiber)
        conn = fiber.Connected_to.outgoing
        for item in conn:
            tmp = item.end
            if tmp['name'] != node['name']:
                fibers['node_name'] = tmp['name']
                fibers['node_url'] = nc.get_node_url(tmp)
        opt_info.append(fibers)
    location_relationships = node.Located_in.outgoing
    return render_to_response('noclook/optical_node_detail.html',
                             {'node': node, 'node_handle': nh, 
                              'last_seen': last_seen, 'expired': expired, 
                              'opt_info': opt_info,
                              'location_relationships': location_relationships},
                              context_instance=RequestContext(request))

@login_required
def host_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = nc.neo4j_data_age(node)
    info = {}
    special_keys = ['hostnames', 'addresses']
    # Handle special keys
    info['hostnames'] = node.get('hostnames', [])
    info['addresses'] = node.get('addresses', [])
    # Add the rest of the keys to the info dict
    for key, value in node.properties.items():
        if key not in special_keys:
            info[key] = value
    # Handle relationships
    service_relationships = node.relationships.incoming(types=['Depends_on'])
    user_relationships = node.relationships.incoming(types=['Uses'])
    provider_relationships = node.relationships.incoming(types=['Provides'])
    owner_relationships = node.relationships.incoming(types=['Owns'])
    return render_to_response('noclook/host_detail.html', 
                              {'node_handle': nh, 'node': node,
                               'last_seen': last_seen, 'expired': expired, 
                               'service_relationships': service_relationships,
                               'info': info, 
                               'user_relationships': user_relationships,
                               'provider_relationships': provider_relationships,
                               'owner_relationships': owner_relationships},
                               context_instance=RequestContext(request))
                
@login_required
def host_service_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = nc.neo4j_data_age(node)
    service_relationships = node.relationships.outgoing(types=['Depends_on'])
    return render_to_response('noclook/host_service_detail.html', 
                              {'node_handle': nh, 'node': node,
                              'last_seen': last_seen, 'expired': expired, 
                              'service_relationships': service_relationships},
                               context_instance=RequestContext(request))
                               
@login_required
def host_provider_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = nc.neo4j_data_age(node)
    host_relationships = node.relationships.outgoing(types=['Provides'])
    return render_to_response('noclook/host_provider_detail.html', 
                              {'node_handle': nh, 'node': node,
                               'last_seen': last_seen, 'expired': expired,
                               'host_relationships': host_relationships},
                               context_instance=RequestContext(request))
                               
@login_required
def host_user_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = nc.neo4j_data_age(node)
    host_relationships = node.relationships.outgoing(types=['Uses'])
    return render_to_response('noclook/host_user_detail.html', 
                              {'node_handle': nh, 'node': node,
                               'last_seen': last_seen, 'expired': expired,
                               'host_relationships': host_relationships},
                               context_instance=RequestContext(request))

@login_required
def cable_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = nc.neo4j_data_age(node)
    connected_rel = node.Connected_to.outgoing
    opt_info = []
    for equip in connected_rel:
        equipment = {}
        conn = equip.end
        equipment['node_name'] = conn['name']
        equipment['node_url'] = nc.get_node_url(conn)
        opt_info.append(equipment)
    return render_to_response('noclook/cable_detail.html',
                              {'node': node, 'node_handle': nh, 
                               'last_seen': last_seen, 'expired': expired, 
                               'opt_info': opt_info},
                               context_instance=RequestContext(request))

@login_required
def peering_partner_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = nc.neo4j_data_age(node)
    # Get services used
    services_rel = node.Uses.outgoing
    # services_rel are relations to bgp groups(Service)
    peering_points = []
    for s_rel in services_rel:
        peering_point = {}
        peering_point['pp_ip'] = s_rel['ip_address']
        peering_point['service'] = s_rel.end['name']
        peering_point['service_url'] = nc.get_node_url(s_rel.end)
        unit_rels = s_rel.end.Depends_on.outgoing
        org_address = ipaddr.IPAddress(s_rel['ip_address'])
        for unit_rel in unit_rels:
            unit_address = ipaddr.IPNetwork(unit_rel['ip_address'])
            if org_address in unit_address:
                peering_point['if_address'] = unit_rel['ip_address']
                peering_point['unit'] = unit_rel.end['name']
                pic = unit_rel.end.Depends_on.outgoing.single.end
                peering_point['pic'] = pic['name']
                peering_point['pic_url'] = nc.get_node_url(pic)
                router = nc.get_root_parent(nc.neo4jdb, pic)
                peering_point['router'] = router['name']
                peering_point['router_url'] = nc.get_node_url(router)
                peering_points.append(peering_point)
    return render_to_response('noclook/peering_partner_detail.html',
                              {'node_handle': nh, 'node': node,
                               'last_seen': last_seen, 'expired': expired,
                               'peering_points': peering_points},
                               context_instance=RequestContext(request))

@login_required
def ip_service_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = nc.neo4j_data_age(node)
    # Get the units dependendant on
    unit_rels = node.Depends_on.outgoing
    service_resources = []
    for unit_rel in unit_rels:
        if_address = ipaddr.IPNetwork(unit_rel['ip_address'])
        interface = {}
        interface['unit'] = unit_rel.end
        interface['if_address'] = unit_rel['ip_address']
        # TODO: If service depends on more than one PIC this won't show the
        # corrent information.
        pic = unit_rel.end.Depends_on.outgoing.single.end
        interface['pic'] = pic
        router = nc.get_root_parent(nc.neo4jdb, pic)
        interface['router'] = router
        interface['relations'] = []
        # Get relations who uses the service
        rel_rels = node.Uses.incoming
        for r_rel in rel_rels:
            org_address = ipaddr.IPAddress(r_rel['ip_address'])
            if org_address in if_address:
                relation = {'rel_address': r_rel['ip_address'],
                            'relation': r_rel.start}
                interface['relations'].append(relation)
        service_resources.append(interface)
    return render_to_response('noclook/ip_service_detail.html',
                              {'node_handle': nh, 'node': node,
                               'last_seen': last_seen, 'expired': expired,
                               'service_resources': service_resources},
                               context_instance=RequestContext(request))

@login_required
def site_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = nc.neo4j_data_age(node)
    info = node.properties
    # Handle relationships
    equipment_relationships = node.relationships.incoming(types=['Located_in'])
    responsible_relationships = node.relationships.incoming(
                                                    types=['Responsible_for'])
    loc_relationships = node.relationships.outgoing(types=['Has'])
    return render_to_response('noclook/site_detail.html', 
                        {'node_handle': nh, 'node': node, 'info': info, 
                        'last_seen': last_seen, 'expired': expired,
                        'equipment_relationships': equipment_relationships, 
                        'responsible_relationships': responsible_relationships,
                        'loc_relationships': loc_relationships},
                        context_instance=RequestContext(request))

@login_required
def site_owner_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = nc.neo4j_data_age(node)
    info = node.properties
    # Handle relationships
    site_relationships = node.relationships.outgoing(types=['Responsible_for'])
    return render_to_response('noclook/site_owner_detail.html', 
                              {'node_handle': nh, 'node': node, 'info': info,
                               'last_seen': last_seen, 'expired': expired,
                               'site_relationships': site_relationships},
                               context_instance=RequestContext(request))

# Visualization views
@login_required
def visualize_json(request, slug, handle_id):
    '''
    Creates a JSON representation of the nodes and its adjecencies.
    This JSON data is then used by JIT (http://thejit.org) to make
    a visual representation.
    '''
    import jitgraph

    # Get the node
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    root_node = nh.get_node()
    # Create the data JSON structure needed
    jsonstr = jitgraph.get_json(root_node)
    return HttpResponse(jsonstr, mimetype='application/json')

@login_required
def visualize(request, slug, handle_id):
    '''
    Visualize view with JS that loads JSON data.
    '''
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    node = nh.get_node()
    return render_to_response('noclook/visualize.html',
                            {'node_handle': nh, 'node': node},
                            context_instance=RequestContext(request))

# Node manipulation views
@login_required
def new_node(request, slug):
    if not request.user.is_staff:
        raise Http404    
    if request.POST:
        # Create the new node
        node_name = request.POST['name']
        node_type = get_object_or_404(NodeType, slug=request.POST['node_types'])
        node_meta_type = request.POST['meta_types'].lower()
        node_handle = NodeHandle(node_name=node_name,
                                node_type=node_type,
                                node_meta_type=node_meta_type,
                                creator=request.user)
        node_handle.save()
        return edit_node(request, slugify(node_handle.node_type), 
                                                         node_handle.handle_id)
    else:
        node_types = get_list_or_404(NodeType)

    return render_to_response('noclook/new_node.html',
                            {'node_types': node_types},
                            context_instance=RequestContext(request))

@login_required
def edit_node(request, slug, handle_id, node=None, message=None):
    '''
    View used to change and add properties to a node, also to delete
    a node relationships.
    '''
    if not request.user.is_staff:
        raise Http404
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    if not node:
        node = nh.get_node()
    # Make a dict of properties you want to be able to change
    node_properties = {}    
    for key, value in node.properties.items():
        try:
            node_properties[key] = json.dumps(value)
        except ValueError:
            node_properties[key] = value
    unwanted_properties = ['handle_id', 'node_type']
    for key in unwanted_properties:
        del node_properties[key]
    
    # Relationships
    # Make a dict of relationships you want to be able to change
    unwanted_relationships = ['Contains', 'Consist_of']
    node_relationships = []
    for rel in node.relationships.all():
        relationship = {'properties': {}}
        if rel.type not in unwanted_relationships:
            relationship['id'] = rel.id
            relationship['start'] = rel.start['name']
            relationship['type'] = rel.type
            relationship['end'] = rel.end['name']
            relationship['properties'].update(rel.properties)
            node_relationships.append(relationship)
    return render_to_response('noclook/edit_node.html',
                            {'node_handle': nh, 'node': node,
                            'node_properties': node_properties,
                            'node_relationships': node_relationships,
                            'message': message},
                            context_instance=RequestContext(request))

@login_required
def save_node(request, slug, handle_id):
    '''
    Updates the node and node_handle with new values.
    '''
    if not request.user.is_staff:
        raise Http404
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    node = nh.get_node()
    if request.POST:
        # request.POST is immutable.
        post = request.POST.copy()
        new_properties = {}
        del post['csrfmiddlewaretoken']
        # Add all new properties
        for i in range(0, len(post)):
            # To make this work we need js in the template to add new
            # input with name new_keyN and new_valueN.
            nk = 'new_key%d' % i
            nv = 'new_value%d' % i
            if (nk in post) and (nv in post):
                #QueryDicts uses lists a values
                new_properties[post[nk]] = post.get(nv)
                del post[nk]
                del post[nv]
        # Add the remaining properties
        for item in post:
            new_properties[item] = post.get(item)
        # Update the node
        node = nc.update_node_properties(nh.node_id, new_properties)
        # Update the node_handle
        nh.node_name = node['name']
        nh.save()
    return edit_node(request, slug, handle_id, node=node)
    
@login_required
def delete_node(request, slug, handle_id):
    '''
    Deletes the NodeHandle from the SQL database and the node from the Neo4j
    database.
    '''    
    if not request.user.is_staff:
        raise Http404
    if request.POST:
        if 'confirmed' in request.POST and \
                                        request.POST['confirmed'] == 'delete':
            nh = get_object_or_404(NodeHandle, pk=handle_id)
            nh.delete()
            return HttpResponseRedirect('/%s/' % slug) 
    return edit_node(request, slug, handle_id)

@login_required
def new_relationship(request, slug, handle_id):
    '''
    Create a new relationship between the node that was edited and another node.
    
    The way to get the nodes that are suitible for relationships have to be
    tought over again. This way is pretty hary.
    '''
    if not request.user.is_staff:
        raise Http404
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    node = nh.get_node()
    message = ''
    if request.POST:
        if request.POST['direction']:
            direction = request.POST['direction']
            node_id = request.POST['nodes']
            other_node = nc.get_node_by_id(node_id)
            rel_type = request.POST['types']
            if direction == 'out':
                rel = nc.make_suitable_relationship(node, other_node, rel_type)
            else:
                rel = nc.make_suitable_relationship(other_node, node, rel_type)
            if rel:
                rel_id = rel.id
                return edit_relationship(request, slug, handle_id, rel_id, rel)
            else:
                message = 'The requested relationship could not be made.' 
        else:
            message = 'You have to choose relationship direction.'
    node_dicts = []
    suitable_nodes = nc.get_suitable_nodes(node)
    for item in ['physical', 'logical', 'relation', 'location']:
        for n in suitable_nodes[item]:
            parent = nc.get_root_parent(n, nc.Incoming.Has)
            if parent:
                name = '%s %s' % (parent['name'], n['name'])      
            else:
                name = n['name']
                node_type = n['node_type']
            node_dicts.append({'name': name, 
                               'id':n.id, 
                               'node_type': node_type})
    return render_to_response('noclook/new_relationship.html',
                            {'node_handle': nh, 'node': node, 
                             'node_dicts': node_dicts, 'message': message},
                            context_instance=RequestContext(request))

@login_required
def edit_relationship(request, slug, handle_id, rel_id, rel=None, message=None):
    '''
    View to update, change or delete relationships properties.
    '''
    if not request.user.is_staff:
        raise Http404
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    if not rel:
        node = nh.get_node()
        rel = nc.get_relationship_by_id(rel_id, node)
    rel_properties = rel.properties
    return render_to_response('noclook/edit_relationship.html',
                            {'node_handle': nh, 'rel': rel, 
                             'rel_properties': rel_properties, 
                             'message': message},
                            context_instance=RequestContext(request))

@login_required
def save_relationship(request, slug, handle_id, rel_id):
    if not request.user.is_staff:
        raise Http404
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    node = nh.get_node()
    rel = nc.get_relationship_by_id(rel_id, node)
    if request.POST:
        # request.POST is immutable.
        post = request.POST.copy()
        new_properties = {}
        del post['csrfmiddlewaretoken']
        # Add all new properties
        for i in range(0, len(post)):
            # To make this work we need js in the template to add new
            # input with name new_keyN and new_valueN.
            nk = 'new_key%d' % i
            nv = 'new_value%d' % i
            if (nk in post) and (nv in post):
                #QueryDicts uses lists a values
                new_properties[post[nk]] = post.get(nv)
                del post[nk]
                del post[nv]
        # Add the remaining properties
        for item in post:
            new_properties[item] = post.get(item)
        # Update the relationships properties
        rel = nc.update_relationship_properties(node.id, rel_id, new_properties)
    return edit_relationship(request, slug, handle_id, rel_id, rel)

@login_required
def delete_relationship(request, slug, handle_id, rel_id):
    '''
    Deletes the relationship if POST['confirmed']==True.
    '''
    if not request.user.is_staff or not request.POST:
        raise Http404
    if 'confirmed' in request.POST.keys():
        nh = get_object_or_404(NodeHandle, pk=handle_id)
        node = nh.get_node()
        message = 'No relationship matching the query was found. Nothing deleted.'
        for rel in node.relationships.all():
            cur_id = str(rel.id)
            if cur_id == rel_id and cur_id in request.POST['confirmed']:
                message = 'Relationship %s %s %s deleted.' % (rel.start['name'],
                                                              rel.type,
                                                              rel.end['name']) 
                rel.delete()
                break                
        return edit_node(request, slug, handle_id, message=message)
    else:            
        message = 'Please confirm the deletion of the relationship.'
        return edit_node(request, slug, handle_id, message=message)
        
# Search views
@login_required
def search(request):
    '''
    Search through nodes either from a POSTed search query or through an
    URL like /slug/key/value/ or /slug/value/.
    '''
    if request.POST:
        value = request.POST.get('query', '') # search for '' if blank
        # See if value is from autocomplete
        index = nc.get_node_index(nc.search_index_name())
        nodes = list(index.query('all', '*%s*' % value))
        if not nodes:
            nodes = nc.get_node_by_value(node_value=value)
        result = []
        for node in nodes:
            nh = get_object_or_404(NodeHandle, pk=node['handle_id'])
            item = {'node': node, 'nh': nh}
            result.append(item)
        return render_to_response('noclook/search_result.html',
                                {'value': value, 'result': result},
                                context_instance=RequestContext(request))
    return HttpResponseRedirect('/')
                            
@login_required
def search_autocomplete(request):
    '''
    Search through a pre determined index for [query]* and returns JSON data
    like below.
    {
     query:'Li',
     suggestions:['Liberia','Liechtenstein','Lithuania'],
     data:['LR','LY','LI','LT']
    }
    '''
    query = request.GET.get('query', None)
    if query:
        ind = nc.get_node_index(nc.search_index_name())
        suggestions = list(n['name'] for n in ind.query('name', '*%s*' % query))
        jsonstr = json.dumps({'query': query, 'suggestions': suggestions,
                              'data': []})
        return HttpResponse(jsonstr, mimetype='application/json')
    return False
    
@login_required
def find_all(request, slug=None, key=None, value=None):
    '''
    Search through nodes either from a POSTed search query or through an
    URL like /slug/key/value/ or /slug/value/.
    '''
    if request.POST:
        value = request.POST.get('query', '') # search for '' if blank
    if slug:
        try:
            node_type = get_object_or_404(NodeType, slug=slug)
            node_handle = node_type.nodehandle_set.all()[0]
            node_meta_type = node_handle.node_meta_type
        except Http404:
            return render_to_response('noclook/search_result.html',
                            {'node_type': slug, 'key': key, 
                             'value': value, 'result': None, 
                             'node_meta_type': None},
                            context_instance=RequestContext(request))
    else:
        node_meta_type = None
        node_type = None
    nodes = nc.get_node_by_value(nc.neo4jdb, node_value=value,
                                 node_property=key)
    result = []
    for node in nodes:
        # Check so that the node_types are equal. A problem with meta type.
        if node_type and not node['node_type'] == str(node_type):
            continue
        nh = get_object_or_404(NodeHandle, pk=node['handle_id'])
        item = {'node': node, 'nh': nh}
        result.append(item)
    return render_to_response('noclook/search_result.html',
                            {'node_type': node_type, 'key': key, 
                             'value': value, 'result': result, 
                             'node_meta_type': node_meta_type},
                            context_instance=RequestContext(request))