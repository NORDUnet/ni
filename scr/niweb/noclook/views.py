from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from niweb.noclook.models import NodeHandle, NodeType

import neo4jclient
import ipaddr
import json

def index(request):
    return render_to_response('noclook/index.html', {},
        context_instance=RequestContext(request))

@login_required
def list_by_type(request, slug):
    type = get_object_or_404(NodeType, slug=slug)
    node_handle_list = type.nodehandle_set.all()
    return render_to_response('noclook/list_by_type.html',
        {'node_handle_list': node_handle_list},
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
    depending_nodes = []
    depends_rel = node.relationships.incoming(types=['Depends_on'])
    for d_rel in depends_rel:
        orgs_rel = d_rel.start.relationships.incoming(types=['Uses'])
        pic_address = ipaddr.IPNetwork(d_rel['ip_address'])
        tmp = []
        tmp.append(d_rel.start)
        for o_rel in orgs_rel:
            org_address = ipaddr.IPAddress(o_rel['ip_address'])
            if org_address in pic_address:
                tmp.append(o_rel.start)
        if len(tmp) > 1: #If any organistations was found
            depending_nodes.append(tmp)
    # Get connected nodes
    connected_nodes = []
    rel_list = node.relationships.incoming(types=['Connected_to'])
    for rel in rel_list:
        connected_nodes.append(rel.start)
    return render_to_response('noclook/pic_detail.html',
        {'node_handle': nh, 'node': node, 'units': units,
        'parent': parent_node, 'depending':depending_nodes,
        'connected':connected_nodes},
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
    for s_rel in services_rel:
        pics_rel = s_rel.end.relationships.outgoing(types="Depends_on")
        org_address = ipaddr.IPAddress(s_rel['ip_address'])
        tmp = []
        tmp.append(s_rel)
        for p_rel in pics_rel:
            pic_address = ipaddr.IPNetwork(p_rel['ip_address'])
            if org_address in pic_address:
                tmp.append(p_rel)
        if len(tmp) > 1: #If any organistations was found
            service_relationships.append(tmp)

    return render_to_response('noclook/peering_partner_detail.html',
        {'node_handle': nh, 'node': node,
        'service_relationships': service_relationships},
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

@login_required
def logout_page(request):
    '''
    Log users out and redirect them to the index.
    '''
    logout(request)
    return HttpResponseRedirect('/')
