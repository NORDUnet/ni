# -*- coding: utf-8 -*-
__author__ = 'lundberg'

# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from re import escape as re_escape
import json
from lucenequerybuilder import Q

from apps.noclook.models import NodeHandle, NodeType
from apps.noclook import arborgraph
import apps.noclook.helpers as h
import norduniclient as nc


def index(request):
    return render_to_response('noclook/index.html', {}, context_instance=RequestContext(request))


@login_required
def logout_page(request):
    """
    Log users out and redirects them to the index.
    """
    logout(request)
    return HttpResponseRedirect('/')


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
    return render_to_response('noclook/visualize/visualize.html', {'node_handle': nh, 'node': node, 'slug': slug},
                              context_instance=RequestContext(request))


@login_required
def visualize_maximize(request, slug, handle_id):
    """
    Visualize view with JS that loads JSON data.
    """
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    node = nh.get_node()
    return render_to_response('noclook/visualize/visualize_maximize.html',
                              {'node_handle': nh, 'node': node, 'slug': slug},
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
    result = []
    if value:
        value = re_escape(value)
        i1 = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
        q = Q('all', '*%s*' % value, wildcard=True)
        nodes = h.iter2list(i1.query(unicode(q)))
        if not nodes:
            nodes = nc.get_node_by_value(nc.neo4jdb, node_value=value)
        if form == 'csv':
            return h.nodes_to_csv([node for node in nodes])
        elif form == 'xls':
            return h.nodes_to_xls([node for node in nodes])
        for node in nodes:
            nh = get_object_or_404(NodeHandle, pk=node['handle_id'])
            item = {'node': node, 'nh': nh}
            result.append(item)
        if len(result) == 1:
            return HttpResponseRedirect(result[0]['nh'].get_absolute_url())
    return render_to_response('noclook/search_result.html', {'value': value, 'result': result, 'posted': posted},
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
        query = re_escape(query)
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
        value = request.POST.get('q', '')  # search for '' if blank
    if slug:
        try:
            node_type = get_object_or_404(NodeType, slug=slug)
            node_handle = node_type.nodehandle_set.all()[0]
            node_meta_type = node_handle.node_meta_type
        except Http404:
            return render_to_response('noclook/search_result.html',
                                      {'node_type': slug, 'key': key, 'value': value, 'result': None,
                                       'node_meta_type': None},
                                      context_instance=RequestContext(request))
    else:
        node_meta_type = None
        node_type = None
    if value:
        nodes = nc.get_node_by_value(nc.neo4jdb, node_value=value, node_property=key)
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
                              {'node_type': node_type, 'key': key, 'value': value, 'result': result,
                               'node_meta_type': node_meta_type},
                              context_instance=RequestContext(request))


# Google maps views
@login_required
def gmaps(request, slug):
    return render_to_response('noclook/google_maps.html', {'slug': slug}, context_instance=RequestContext(request))


@login_required
def gmaps_json(request, slug):
    """
    Directs gmap json requests to the right view.
    """
    gmap_views = {
        'sites': gmaps_sites,
        'optical-nodes': gmaps_optical_nodes
    }
    try:
        return gmap_views[slug](request)
    except KeyError:
        raise Http404


@login_required
def gmaps_sites(request):
    """
    Return a json object with node dicts.
    {
        nodes: [
            {
            name: '',
            url: '',
            lng: 0.0,
            lat: 0.0
            },
        ],
        edges: []
    }
    """
    node_types_index = nc.get_node_index(nc.neo4jdb, 'node_types')
    hits = node_types_index['node_type']['Site']
    site_list = []
    for node in hits:
        try:
            site = {
                'name': node['name'],
                'url': h.get_node_url(node),
                'lng': float(str(node.getProperty('longitude', 0))),
                'lat': float(str(node.getProperty('latitude', 0)))
            }
        except KeyError:
            continue
        site_list.append(site)
    response = HttpResponse(mimetype='application/json')
    json.dump({'nodes': site_list, 'edges': []}, response)
    return response


#@login_required
def gmaps_optical_nodes(request):
    """
    Return a json object with dicts of optical node and cables.
    {
    nodes: [
        {
        name: '',
        url: '',
        lng: 0.0,
        lat: 0.0
        },
    ],
    edges: [
        {
        name: '',
        url: '',
        end_points: [{lng: 0.0, lat: 0.0,},]
        }
    ]
    """
    # Cypher query to get all cables with cable type fiber that are connected
    # to two optical node.
    q = """
        START cable = node:node_types(node_type="Cable")
        MATCH cable-[Connected_to]->port
        WHERE cable.cable_type = "Dark Fiber"
        WITH cable, port
        MATCH port<-[:Has*0..]-equipment
        WHERE equipment.node_type = "Optical Node" AND NOT equipment.type? =~ "(?i).*tss.*"
        WITH cable, port, equipment
        MATCH p2=equipment-[:Located_in]->()<-[:Has*0..]-loc
        WHERE loc.node_type = "Site"
        RETURN cable, equipment, loc
        """
    hits = nc.neo4jdb.query(q)
    nodes = {}
    edges = {}
    for hit in hits:
        node = {
            'name': hit['equipment']['name'],
            'url': h.get_node_url(hit['equipment']),
            'lng': float(str(hit['loc'].getProperty('longitude', 0))),
            'lat': float(str(hit['loc'].getProperty('latitude', 0)))
        }
        coords = {
            'lng': float(str(hit['loc'].getProperty('longitude', 0))),
            'lat': float(str(hit['loc'].getProperty('latitude', 0)))
        }
        edge = {
            'name': hit['cable']['name'],
            'url': h.get_node_url(hit['cable']),
            'end_points': [coords]
        }
        nodes[hit['equipment']['name']] = node
        if hit['cable']['name'] in edges:
            edges[hit['cable']['name']]['end_points'].append(coords)
        else:
            edges[hit['cable']['name']] = edge
    response = HttpResponse(mimetype='application/json')
    json.dump({'nodes': nodes.values(), 'edges': edges.values()}, response)
    return response


@login_required
def qr_lookup(request, name):
    search_index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
    hits = h.iter2list(search_index['name'][name])
    if len(hits) == 1:
        nh = get_object_or_404(NodeHandle, pk=hits[0]['handle_id'])
        return HttpResponseRedirect(nh.get_absolute_url())
    return render_to_response('noclook/qr_result.html', {'hits': hits, 'name': name},
                              context_instance=RequestContext(request))


@login_required
def ip_address_lookup(request):
    if request.POST:
        ip_address = request.POST.get('ip_address', None)
        if ip_address:
            hostname = h.get_hostname_from_address(ip_address)
            return HttpResponse(json.dumps(hostname), mimetype='application/json')
    raise Http404


@login_required
def json_table_to_file(request):
    if request.POST:
        file_format = request.POST.get('format', None)
        data = request.POST.get('data', None)
        header = request.POST.get('header', None)
        table = json.loads(data)
        header = json.loads(header)
        if table and file_format == 'csv':
            return h.dicts_to_csv(table, header)
        elif table and file_format == 'xls':
            return h.dicts_to_xls_response(table, header)
    raise Http404
