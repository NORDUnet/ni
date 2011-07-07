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
import copy

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
    node_type = get_object_or_404(NodeType, slug='peering-partner')
    partner_list = []
    for nh in node_type.nodehandle_set.all():
        partner = {}
        node = nh.get_node()
        partner['name'] = node.get('name', None)
        partner['as_number'] = node.get('as_number', None)
        partner['url'] = nh.get_absolute_url()
        partner_list.append(partner)
    return render_to_response('noclook/list_peering_partners.html',
                                {'partner_list': partner_list},
                                context_instance=RequestContext(request))

@login_required
def list_by_master(request, handle_id, slug):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    master = nh.get_node()
    # Get all outgoing related nodes
    node_list = master.traverse()
    node_handle_list = []
    node_type = get_object_or_404(NodeType, slug=slug)
    for node in node_list:
        if node['node_type'] == str(node_type):
            node_handle_list.append(get_object_or_404(NodeHandle,
                                        pk=node['handle_id']))
    return render_to_response('noclook/list_by_type.html',
        {'node_handle_list': node_handle_list},
        context_instance=RequestContext(request))

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
    # Get all the routers PICs
    pic_nodes = node.traverse(types=nc.Outgoing.Has)
    return render_to_response('noclook/router_detail.html',
        {'node_handle': nh, 'node': node, 'pic_nodes': pic_nodes},
        context_instance=RequestContext(request))

@login_required
def pic_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    # Get PIC units
    units = json.loads(node['units'])
    # Get the master node
    rel_list = node.relationships.incoming(types=['Has'])
    parent_node = rel_list[0].start
    # Get depending nodes
    depending_relationships = []
    depends_rel = node.relationships.incoming(types=['Depends_on'])
    for d_rel in depends_rel:
        orgs_rel = d_rel.start.relationships.incoming(types=['Uses'])
        pic_address = ipaddr.IPNetwork(d_rel['ip_address'])
        tmp = []
        tmp.append(d_rel)
        for o_rel in orgs_rel:
            org_address = ipaddr.IPAddress(o_rel['ip_address'])
            if org_address in pic_address:
                tmp.append(o_rel)
        if len(tmp) > 1: #If any organistations was found
            depending_relationships.append(tmp)
    # Get connected nodes
    connected_nodes = []
    rel_list = node.relationships.incoming(types=['Connected_to'])
    for rel in rel_list:
        connected_nodes.append(rel.start)
    return render_to_response('noclook/pic_detail.html',
        {'node_handle': nh, 'node': node, 'units': units,
        'parent': parent_node, 'depending':depending_relationships,
        'connected':connected_nodes},
        context_instance=RequestContext(request))

@login_required
def optical_node_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    info = {}
    info['name'] = node['name']
    info['node_url'] = nc.get_node_url(node.id)
    info.update(node.properties)
    #get incoming rels of fibers
    connected_rel = node.relationships.incoming(types=['Connected_to'])
    opt_info = []
    for rel in connected_rel:
        fibers = {}
        fiber = rel.start
        fibers['fiber_name'] = fiber['name']
        fibers['fiber_url'] = nc.get_node_url(fiber.id)
        conn = fiber.relationships.outgoing(types = ['Connected_to'])
        for item in conn:
            tmp = item.end
            if tmp['name'] != node['name']:
                fibers['node_name'] = tmp['name']
                fibers['node_url'] = nc.get_node_url(tmp.id)
        opt_info.append(fibers)
    return render_to_response('noclook/optical_node_detail.html',
        {'node': node, 'node_handle': nh, 'info': info, 'opt_info': opt_info},
        context_instance=RequestContext(request))

#@login_required
#def host_node_detail(request, handle_id):
    #nh = get_object_or_404(NodeHandle, pk=handle_id)
    ## Get node from neo4j-database
    #node = nh.get_node()
    #info = {}
    #info['name'] = node['name']
    #info['node_url'] = get_node_url(node.id)

    #return render_to_response('noclook/host_node_detail.html',
        #{'node_handle': nh, 'info': info, 'node': node, 'lista': lista},
        #context_instance=RequestContext(request))

@login_required
def cable_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    info = {}
    info['name'] = node['name']
    info['node_url'] = nc.get_node_url(node.id)
    info.update(node.properties)
    connected_rel = node.relationships.outgoing(types=['Connected_to'])
    opt_info = []
    for equip in connected_rel:
        equipment = {}
        conn = equip.end
        equipment['node_name'] = conn['name']
        equipment['node_url'] = nc.get_node_url(conn.id)
        opt_info.append(equipment)
    return render_to_response('noclook/cable_detail.html',
        {'node': node, 'node_handle': nh, 'info': info, 'opt_info': opt_info},
        context_instance=RequestContext(request))

@login_required
def peering_partner_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    # Get services used
    services_rel = node.relationships.outgoing(types=['Uses'])
    # services_rel are relatios to bgp groups(Service)
    peering_points = []
    for s_rel in services_rel:
        peering_point = {}
        peering_point['pp_ip'] = s_rel['ip_address']
        peering_point['service'] = s_rel.end['name']
        peering_point['service_url'] = nc.get_node_url(s_rel.end.id)
        pics_rel = s_rel.end.relationships.outgoing(types="Depends_on")
        #pics_rel is a list of nodes with equipments/cables and services
        org_address = ipaddr.IPAddress(s_rel['ip_address'])
        for p_rel in pics_rel:
            pic_address = ipaddr.IPNetwork(p_rel['ip_address'])
            if org_address in pic_address:
                peering_point['pic_ip'] = p_rel['ip_address']
                peering_point['pic'] = p_rel.end['name']
                peering_point['pic_url'] = nc.get_node_url(p_rel.end.id)
                router = nc.get_root_parent(p_rel.end, nc.Incoming.Has)
                peering_point['router'] = router['name']
                peering_point['router_url'] = nc.get_node_url(router.id)
                peering_points.append(peering_point)
    return render_to_response('noclook/peering_partner_detail.html',
        {'node_handle': nh, 'node': node,
        'peering_points': peering_points},
        context_instance=RequestContext(request))

@login_required
def ip_service_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    # Get PICs dependendant on
    pics_rel = node.relationships.outgoing(types=['Depends_on'])
    # Get Organisations who uses the service
    orgs_rel = node.relationships.incoming(types=['Uses'])
    service_relationships = []
    for p_rel in pics_rel:
        pic_address = ipaddr.IPNetwork(p_rel['ip_address'])
        tmp = []
        tmp.append(p_rel)
        for o_rel in orgs_rel:
            org_address = ipaddr.IPAddress(o_rel['ip_address'])
            if org_address in pic_address:
                tmp.append(o_rel)
        if len(tmp) > 1: #If any organistations was found
            service_relationships.append(tmp)
    return render_to_response('noclook/ip_service_detail.html',
        {'node_handle': nh, 'node': node,
        'service_relationships': service_relationships},
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
    node_properties = copy.copy(node.properties)
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
            nc.delete_node(nh.node_id)
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
        index = nc.get_node_index('search_test1')
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
    raise Http404
                            
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
        ind = nc.get_node_index('search_test1')
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
    nodes = nc.get_node_by_value(node_value=value, 
                                 meta_node_name=node_meta_type, 
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