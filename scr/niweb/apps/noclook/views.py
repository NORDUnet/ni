from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.conf import settings
from django.template import RequestContext
from django.template.defaultfilters import slugify
from niweb.apps.noclook.models import NodeHandle, NodeType

import neo4jclient
import ipaddr
import json
import copy

# Tools, consider moving these to another file
def get_node_url(node):
    '''
    Returns a relative url to a node.
    '''
    return '%s%s/%d/' % (settings.NIWEB_URL, slugify(node['type']),
                                                    node['handle_id'])
# end tools

def index(request):
    return render_to_response('noclook/index.html', {},
        context_instance=RequestContext(request))

@login_required
def logout_page(request):
    '''
    Log users out and redirect them to the index.
    '''
    logout(request)
    return HttpResponseRedirect('/')

# List views
@login_required
def list_by_type(request, slug):
    type = get_object_or_404(NodeType, slug=slug)
    node_handle_list = type.nodehandle_set.all()
    return render_to_response('noclook/list_by_type.html',
        {'node_handle_list': node_handle_list, 'node_type': type},
        context_instance=RequestContext(request))

@login_required
def list_by_master(request, handle_id, slug):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    nc = neo4jclient.Neo4jClient()
    master = nc.get_node_by_id(nh.node_id)
    # Get all outgoing related nodes
    node_list = master.traverse()
    node_handle_list = []
    type = get_object_or_404(NodeType, slug=slug)
    for node in node_list:
        if node['type'] == str(type):
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
    nc = neo4jclient.Neo4jClient()
    node = nc.get_node_by_id(nh.node_id)
    return render_to_response('noclook/detail.html',
        {'node_handle': nh, 'node': node},
        context_instance=RequestContext(request))

@login_required
def router_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    nc = neo4jclient.Neo4jClient()
    node = nc.get_node_by_id(nh.node_id)
    # Get all the routers PICs
    pic_nodes = node.traverse(types=nc.Outgoing.Has)
    return render_to_response('noclook/router_detail.html',
        {'node_handle': nh, 'node': node, 'pic_nodes': pic_nodes},
        context_instance=RequestContext(request))

@login_required
def pic_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    nc = neo4jclient.Neo4jClient()
    node = nc.get_node_by_id(nh.node_id)
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
    nc = neo4jclient.Neo4jClient()
    node = nc.get_node_by_id(nh.node_id)
    info = {}
    info['name'] = node['name']
    info['node_url'] = get_node_url(node)
    #get incoming rels of fibers
    connected_rel = node.relationships.incoming(types=['Connected_to'])
    opt_info = []
    for rel in connected_rel:
        fibers = {}
        fiber = rel.start
        fibers['fiber_name'] = fiber['name']
        fibers['fiber_url'] = get_node_url(fiber)
        conn = fiber.relationships.outgoing(types = ['Connected_to'])
        for item in conn:
            tmp = item.end
            if tmp['name'] != node['name']:
                fibers['node_name'] = tmp['name']
                fibers['node_url'] = get_node_url(tmp)
        opt_info.append(fibers)
    return render_to_response('noclook/optical_node_detail.html',
        {'node_handle': nh, 'info': info, 'opt_info': opt_info},
        context_instance=RequestContext(request))

#@login_required
#def host_node_detail(request, handle_id):
    #nh = get_object_or_404(NodeHandle, pk=handle_id)
    ## Get node from neo4j-database
    #nc = neo4jclient.Neo4jClient()
    #node = nc.get_node_by_id(nh.node_id)
    #info = {}
    #info['name'] = node['name']
    #info['node_url'] = get_node_url(node)

    #return render_to_response('noclook/host_node_detail.html',
        #{'node_handle': nh, 'info': info, 'node': node, 'lista': lista},
        #context_instance=RequestContext(request))

@login_required
def cable_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    nc = neo4jclient.Neo4jClient()
    node = nc.get_node_by_id(nh.node_id)
    info = {}
    info['name'] = node['name']
    info['node_url'] = get_node_url(node)
    if node['cable_type'] == 'TP':
        info['type'] == 'copper cable'
    elif node['cable_type'] == 'Fiber':
        info['type'] = 'optic fiber'
    else:
        info['cable_type'] = node['type']
    connected_rel = node.relationships.outgoing(types=['Connected_to'])
    opt_info = []
    for equip in connected_rel:
        equipment = {}
        conn = equip.end
        equipment['node_name'] = conn['name']
        equipment['node_url'] = get_node_url(conn)
        opt_info.append(equipment)
    return render_to_response('noclook/cable_detail.html',
        {'node_handle': nh, 'info': info, 'opt_info': opt_info, 'node': node },
        context_instance=RequestContext(request))

@login_required
def peering_partner_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    nc = neo4jclient.Neo4jClient()
    node = nc.get_node_by_id(nh.node_id)
    # Get services used
    service_relationships = []
    services_rel = node.relationships.outgoing(types=['Uses'])
    # services_rel are relatios to bgp groups(Service)
    peering_points = []

    for s_rel in services_rel:
        peering_point = {}
        peering_point['pp_ip'] = s_rel['ip_address']
        peering_point['service'] = s_rel.end['name']
        peering_point['service_url'] = get_node_url(s_rel.end)
        pics_rel = s_rel.end.relationships.outgoing(types="Depends_on")
        #pics_rel is a list of nodes with equipments/cables and services
        org_address = ipaddr.IPAddress(s_rel['ip_address'])
        for p_rel in pics_rel:
            pic_address = ipaddr.IPNetwork(p_rel['ip_address'])
            if org_address in pic_address:
                peering_point['pic_ip'] = p_rel['ip_address']
                peering_point['pic'] = p_rel.end['name']
                peering_point['pic_url'] = get_node_url(p_rel.end)
                router = nc.get_root_parent(p_rel.end, nc.Incoming.Has)
                peering_point['router'] = router['name']
                peering_point['router_url'] = get_node_url(router)
                peering_points.append(peering_point)

    return render_to_response('noclook/peering_partner_detail.html',
        {'node_handle': nh, 'node': node,
        'peering_points': peering_points},
        context_instance=RequestContext(request))

@login_required
def ip_service_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    nc = neo4jclient.Neo4jClient()
    node = nc.get_node_by_id(nh.node_id)
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
    from django.http import HttpResponse
    import jitgraph

    # Get the node
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    nc = neo4jclient.Neo4jClient()
    root_node = nc.get_node_by_id(nh.node_id)

    # Create the data JSON structure needed
    jsonstr = jitgraph.get_json(root_node)

    return HttpResponse(jsonstr, mimetype='application/json')

@login_required
def visualize(request, slug, handle_id):
    '''
    Visualize view with JS that loads JSON data.
    '''
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    nc = neo4jclient.Neo4jClient()
    node = nc.get_node_by_id(nh.node_id)
    return render_to_response('noclook/visualize.html',
                            {'node_handle': nh, 'node': node},
                            context_instance=RequestContext(request))

# Node manipulation views
@login_required
def edit_node(request, slug, handle_id, node=None):
    '''
    View used to change and add properties to a node, also to delete
    a node relationships.
    '''
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    nc = neo4jclient.Neo4jClient()
    if not node:
        node = nc.get_node_by_id(nh.node_id)
    # Make a dict of properties you want to be able to change
    node_properties = copy.copy(node.properties)
    unwanted_properties = ['handle_id', 'type']
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
                            'node_relationships': node_relationships},
                            context_instance=RequestContext(request))

@login_required
def save_node(request, slug, handle_id):
    '''
    Updates the node and node_handle with new values.
    '''
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    nc = neo4jclient.Neo4jClient()
    node = nc.get_node_by_id(nh.node_id)

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

    return edit_node(request, slug, handle_id, node)

@login_required
def delete_relationship(request, slug, handle_id):
    '''
    Deletes the relationship if POST['confirmed']==True.
    '''
    pass
    return edit_node(request, slug, handle_id, node)
