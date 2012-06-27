# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
import ipaddr
import json
import arborgraph
from lucenequerybuilder import Q

from niweb.apps.noclook.models import NodeHandle, NodeType
import niweb.apps.noclook.helpers as h
import norduni_client as nc


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
    return render_to_response('noclook/list/list_by_type.html',
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
        try:
            partner['as_number'] = node['as_number']
        except KeyError:
            partner['as_number'] = ''
        partner['peering_partner'] = node
        partner_list.append(partner)
    return render_to_response('noclook/list/list_peering_partners.html',
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
    return render_to_response('noclook/list/list_hosts.html',
                                {'host_list': host_list},
                                context_instance=RequestContext(request))
                                
@login_required
def list_sites(request):
    node_types_index = nc.get_node_index(nc.neo4jdb, 'node_types')
    hits = node_types_index['node_type']['Site']
    site_list = []
    for node in hits:
        site = {}
        site['name'] = node['name']
        try:
            site['country_code'] = node['country_code']
            site['country'] = node['country']
        except KeyError:
            site['country_code'] = ''
        site['site'] = node
        site_list.append(site)
    return render_to_response('noclook/list/list_sites.html',
                                {'site_list': site_list},
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
    return render_to_response('noclook/detail/detail.html',
        {'node_handle': nh, 'node': node},
        context_instance=RequestContext(request))

@login_required
def router_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
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
    location = h.get_location(node)
    for address in loopback_addresses:
        try:
            ipaddr.IPNetwork(address)
        except ValueError:
            # Remove the ISO address
            loopback_addresses.remove(address)
    return render_to_response('noclook/detail/router_detail.html',
        {'node_handle': nh, 'node': node, 'pics': pics, 'last_seen': last_seen,
        'expired': expired, 'location': location,
        'loopback_addresses': loopback_addresses},
        context_instance=RequestContext(request))

@login_required
def pic_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Get the top parent node
    router = nc.get_root_parent(nc.neo4jdb, node)[0]
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
    return render_to_response('noclook/detail/pic_detail.html',
        {'node_handle': nh, 'node': node, 'router': router, 
         'last_seen': last_seen, 'expired': expired, 'units': units,
         'depending_services': depending_services}, 
         context_instance=RequestContext(request))

@login_required
def optical_node_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    #get incoming rels of fibers
    connected_rel = node.Connected_to.incoming
    opt_info = []
    for rel in connected_rel:
        fibers = {}
        fiber = rel.start
        fibers['fiber_name'] = fiber['name']
        fibers['fiber_url'] = h.get_node_url(fiber)
        conn = fiber.Connected_to.outgoing
        for item in conn:
            tmp = item.end
            if tmp['name'] != node['name']:
                fibers['node_name'] = tmp['name']
                fibers['node_url'] = h.get_node_url(tmp)
        opt_info.append(fibers)
    location = h.get_location(node)
    return render_to_response('noclook/detail/optical_node_detail.html',
                             {'node': node, 'node_handle': nh, 
                              'last_seen': last_seen, 'expired': expired, 
                              'opt_info': opt_info,
                              'location': location},
                              context_instance=RequestContext(request))

@login_required
def host_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Handle relationships
    service_relationships = h.iter2list(node.Depends_on.incoming)
    user_relationships = h.iter2list(node.Uses.incoming)
    provider_relationships = h.iter2list(node.Provides.incoming)
    owner_relationships = h.iter2list(node.Owns.incoming)
    location = h.get_location(node)
    return render_to_response('noclook/detail/host_detail.html', 
                              {'node_handle': nh, 'node': node,
                               'last_seen': last_seen, 'expired': expired, 
                               'service_relationships': service_relationships, 
                               'user_relationships': user_relationships,
                               'provider_relationships': provider_relationships,
                               'owner_relationships': owner_relationships,
                               'location': location},
                               context_instance=RequestContext(request))
                
@login_required
def host_service_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    service_relationships = h.iter2list(node.Depends_on.outgoing)
    return render_to_response('noclook/detail/host_service_detail.html', 
                              {'node_handle': nh, 'node': node,
                              'last_seen': last_seen, 'expired': expired, 
                              'service_relationships': service_relationships},
                               context_instance=RequestContext(request))
                               
@login_required
def host_provider_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    host_relationships = h.iter2list(node.Provides.outgoing)
    return render_to_response('noclook/detail/host_provider_detail.html', 
                              {'node_handle': nh, 'node': node,
                               'last_seen': last_seen, 'expired': expired,
                               'host_relationships': host_relationships},
                               context_instance=RequestContext(request))
                               
@login_required
def host_user_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    host_relationships = h.iter2list(node.Uses.outgoing) + h.iter2list(node.Owns.outgoing)
    return render_to_response('noclook/detail/host_user_detail.html', 
                              {'node_handle': nh, 'node': node,
                               'last_seen': last_seen, 'expired': expired,
                               'host_relationships': host_relationships},
                               context_instance=RequestContext(request))

@login_required
def cable_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    connections = h.get_connected_cables(node)
    return render_to_response('noclook/detail/cable_detail.html',
                              {'node': node, 'node_handle': nh, 
                               'last_seen': last_seen, 'expired': expired, 
                               'connections': connections},
                               context_instance=RequestContext(request))

@login_required
def peering_partner_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Get services used
    services_rel = node.Uses.outgoing
    # services_rel are relations to bgp groups(Service)
    peering_points = []
    for s_rel in services_rel:
        peering_point = {}
        peering_point['pp_ip'] = s_rel['ip_address']
        peering_point['service'] = s_rel.end['name']
        peering_point['service_url'] = h.get_node_url(s_rel.end)
        unit_rels = s_rel.end.Depends_on.outgoing
        org_address = ipaddr.IPAddress(s_rel['ip_address'])
        for unit_rel in unit_rels:
            unit_address = ipaddr.IPNetwork(unit_rel['ip_address'])
            if org_address in unit_address:
                peering_point['if_address'] = unit_rel['ip_address']
                peering_point['unit'] = unit_rel.end['name']
                pic = unit_rel.end.Depends_on.outgoing.single.end
                peering_point['pic'] = pic['name']
                peering_point['pic_url'] = h.get_node_url(pic)
                router = nc.get_root_parent(nc.neo4jdb, pic)[0]
                peering_point['router'] = router['name']
                peering_point['router_url'] = h.get_node_url(router)
                peering_points.append(peering_point)
    return render_to_response('noclook/detail/peering_partner_detail.html',
                              {'node_handle': nh, 'node': node,
                               'last_seen': last_seen, 'expired': expired,
                               'peering_points': peering_points},
                               context_instance=RequestContext(request))

@login_required
def ip_service_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Get the units dependendant on
    unit_rels = node.Depends_on.outgoing
    service_resources = []
    for unit_rel in unit_rels:
        if_address = ipaddr.IPNetwork(unit_rel['ip_address'])
        interface = {}
        interface['unit'] = unit_rel.end
        interface['if_address'] = unit_rel['ip_address']
        # TODO: If service depends on more than one PIC this won't show the correct information.
        pic = unit_rel.end.Depends_on.outgoing.single.end
        interface['pic'] = pic
        router = nc.get_root_parent(nc.neo4jdb, pic)[0]
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
    return render_to_response('noclook/detail/ip_service_detail.html',
                              {'node_handle': nh, 'node': node,
                               'last_seen': last_seen, 'expired': expired,
                               'service_resources': service_resources},
                               context_instance=RequestContext(request))

@login_required
def site_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Handle relationships
    equipment_relationships = h.iter2list(node.Located_in.incoming)
    responsible_relationships = h.iter2list(node.Responsible_for.incoming)
    location_relationships = h.iter2list(h.get_racks_and_equipment(node))
    return render_to_response('noclook/detail/site_detail.html', 
                        {'node_handle': nh, 'node': node,
                         'last_seen': last_seen, 'expired': expired,
                         'equipment_relationships': equipment_relationships, 
                         'responsible_relationships': responsible_relationships,
                         'location_relationships': location_relationships},
                         context_instance=RequestContext(request))

@login_required
def site_owner_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Handle relationships
    site_relationships = h.iter2list(node.Responsible_for.outgoing)
    return render_to_response('noclook/detail/site_owner_detail.html', 
                              {'node_handle': nh, 'node': node,
                               'last_seen': last_seen, 'expired': expired,
                               'site_relationships': site_relationships},
                               context_instance=RequestContext(request))

@login_required
def rack_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Get equipment in rack
    physical_relationships = h.iter2list(node.Located_in.incoming)
    # Get rack location
    location = h.get_place(node)
    return render_to_response('noclook/detail/rack_detail.html',
                             {'node': node, 'node_handle': nh, 
                              'last_seen': last_seen, 'expired': expired, 
                              'physical_relationships': physical_relationships,
                              'location': location},
                              context_instance=RequestContext(request))
                              
@login_required
def odf_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Get ports in ODF
    connections = h.get_connected_equipment(node)
    # Get location
    location = h.get_location(node)
    return render_to_response('noclook/detail/odf_detail.html',
                             {'node': node, 'node_handle': nh, 
                              'last_seen': last_seen, 'expired': expired, 
                              'connections': connections,
                              'location': location},
                              context_instance=RequestContext(request))
                              
@login_required
def port_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Get cables connected to the port
    connected_to_rels = h.iter2list(node.Connected_to.incoming)
    # Get location
    location = h.get_place(node)
    return render_to_response('noclook/detail/port_detail.html',
                             {'node': node, 'node_handle': nh, 
                              'last_seen': last_seen, 'expired': expired, 
                              'connected_to_rels': connected_to_rels,
                              'location': location},
                              context_instance=RequestContext(request))


# Visualization views
@login_required
def visualize_json(request, node_id):
    """
    Creates a JSON representation of the node and the adjacent nodes.
    This JSON data is then used by Arbor.js (http://arborjs.org/) to make
    a visual representation.
    """
    # Get the node
    root_node = nc.get_node_by_id(nc.neo4jdb, node_id)
    if root_node:
        # Create the data JSON structure needed
        graph_dict = arborgraph.create_generic_graph(root_node)
        jsonstr = arborgraph.get_json(graph_dict)
    else:
        jsonstr = '{}'
    return HttpResponse(jsonstr, mimetype='application/json')

@login_required
def visualize(request, slug, handle_id):
    """
    Visualize view with JS that loads JSON data.
    """
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    node = nh.get_node()
    return render_to_response('noclook/visualize/visualize.html',
                            {'node_handle': nh, 'node': node},
                            context_instance=RequestContext(request))

@login_required
def visualize_maximize(request, slug, handle_id):
    """
    Visualize view with JS that loads JSON data.
    """
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    node = nh.get_node()
    return render_to_response('noclook/visualize/visualize_maximize.html',
                            {'node_handle': nh, 'node': node},
                            context_instance=RequestContext(request))
        
# Search views
@login_required
def search(request, value='', form=None):
    """
    Search through nodes either from a POSTed search query or through an
    URL like /slug/key/value/ or /slug/value/.
    """
    posted = False
    if request.POST:
        value = request.POST.get('q', '')
        posted = True
    # See if the value is indexed
    i1 = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
    q = Q('all', '*%s*' % value, wildcard=True)
    nodes = h.iter2list(i1.query(unicode(q)))
    if not nodes:
        nodes = nc.get_node_by_value(nc.neo4jdb, node_value=value)
    result = []
    if form == 'csv':
        return h.nodes_to_csv([node for node in nodes])
    elif form == 'xls':
        return h.nodes_to_xls([node for node in nodes])
    for node in nodes:
        nh = get_object_or_404(NodeHandle, pk=node['handle_id'])
        item = {'node': node, 'nh': nh}
        result.append(item)
    return render_to_response('noclook/search_result.html',
                            {'value': value, 'result': result,
                             'posted': posted},
                            context_instance=RequestContext(request))    

                            
@login_required
def search_autocomplete(request):
    """
    Search through a pre determined index for *[query]* and returns JSON data
    like below.
    {
     query:'Li',
     suggestions:['Liberia','Liechtenstein','Lithuania'],
     data:['LR','LY','LI','LT']
    }
    """
    response = HttpResponse(mimetype='application/json')
    query = request.GET.get('query', None)
    if query:
        i1 = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
        q = Q('name', '*%s*' % query, wildcard=True)
        suggestions = []
        for node in i1.query(unicode(q)):
            suggestions.append(node['name'])
        d = {'query': query, 'suggestions': suggestions, 'data': []}
        json.dump(d, response)
        return response
    return False
    
@login_required
def find_all(request, slug='', key='', value='', form=None):
    """
    Search through nodes either from a POSTed search query or through an
    URL like /slug/key/value/, /slug/value/ /key/value/, /value/ or /key/.
    """
    if request.POST:
        value = request.POST.get('q', '') # search for '' if blank
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
    if value:
        nodes = nc.get_node_by_value(nc.neo4jdb, node_value=value,
                                 node_property=key)
    else:
        node_types_index = nc.get_node_index(nc.neo4jdb, 'node_types')
        nodes = node_types_index['node_type'][str(node_type)]
    if form == 'csv':
        return h.nodes_to_csv([node for node in nodes if node['node_type'] == str(node_type)])
    elif form == 'xls':
        return h.nodes_to_xls([node for node in nodes if node['node_type'] == str(node_type)])
    elif form == 'json':
        # TODO:
        pass
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
# Google maps views
@login_required
def gmaps(request, slug):
    return render_to_response('noclook/google_maps.html', {'slug': slug},
        context_instance=RequestContext(request))
        
@login_required
def gmaps_json(request, slug):
    """
    Directs gmap json requests to the right view.
    """
    gmap_views = {'sites': gmaps_sites, 'optical-nodes': gmaps_optical_nodes}
    try:    
        return gmap_views[slug](request)
    except KeyError:
        raise Http404

@login_required
def gmaps_sites(request):
    """
    Return a json list with site dicts.
    [{
        name: '',
        type: 'node',
        lng: 0.0,
        lat: 0.0
    }, ...]
    """
    node_types_index = nc.get_node_index(nc.neo4jdb, 'node_types')
    hits = node_types_index['node_type']['Site']
    site_list = []
    for node in hits:
        try:
            site = {}
            site['id'] = node.id
            site['name'] = node['name']
            site['type'] = 'node'
            site['lng'] = node['longitude']
            site['lat'] = node['latitude']
        except KeyError:
            pass
        if site:
            site_list.append(site)
    jsonstr = json.dumps(site_list)
    return HttpResponse(jsonstr, mimetype='application/json')

@login_required
def gmaps_optical_nodes(request):
    """
    Return a json list with dicts of optical node and cables.
    [{
        name: '',
        type: 'node',
        lng: 0.0,
        lat: 0.0,
    },{
        name: '',
        type: 'edge',
        start_lng: 0.0,
        start_lat: 0.0,
        end_lng: 0.0,
        end_lat: 0.0
    }]
    """
    # Cypher query to get all cables with cable type fiber that are connected
    # to two optical node.
    cypher_query = '''
        START optical_node = node:node_types(node_type="Optical Node")
        MATCH optical_node<-[:Connected_to]-cable-[Connected_to]->other_optical_node
        WHERE (cable.cable_type = "Fiber") and not (optical_node.type? =~ /.*tss.*/)
        RETURN distinct cable
        '''
    query = nc.neo4jdb.query(cypher_query)
    optical_node_list = []
    for hit in query:
        cords = []
        for rel in hit['cable'].Connected_to.outgoing:
            for loc_rel in rel.end.Located_in.outgoing:
                lng = loc_rel.end['longitude']
                lat = loc_rel.end['latitude']
            node = {'name': rel.end['name'], 'type': 'node', 'lng': lng,
                    'lat': lat}
            cords.append({'lng': lng, 'lat': lat})
            optical_node_list.append(node)
        edge = {'name': hit['cable']['name'], 'type': 'edge'}
        # TODO: Needs to be revisited when/if cables terminate in more than two points.
        if len(cords) == 2:
            edge['start_lng'] = cords[0]['lng']
            edge['start_lat'] = cords[0]['lat']
            edge['end_lng'] = cords[1]['lng']
            edge['end_lat'] = cords[1]['lat']
            optical_node_list.append(edge)
        else:
            raise Exception('Fiber cable terminates in too many points.')
    response = HttpResponse(mimetype='application/json')
    json.dump(optical_node_list, response)
    return response

@login_required
def qr_lookup(request, name):
    search_index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
    hits = h.iter2list(search_index['name'][name])
    if len(hits) == 1:
        nh = get_object_or_404(NodeHandle, pk=hits[0]['handle_id'])
        return HttpResponseRedirect(nh.get_absolute_url())
    return render_to_response('noclook/qr_result.html',
            {'hits': hits, 'name': name}, context_instance=RequestContext(request))