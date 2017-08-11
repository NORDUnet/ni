# -*- coding: utf-8 -*-
__author__ = 'lundberg'

# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from re import escape as re_escape
import json

from apps.noclook.models import NodeHandle, NodeType
from apps.noclook import arborgraph
from apps.noclook import helpers
import norduniclient as nc


def index(request):
    return render(request, 'noclook/index.html', {})


@login_required
def logout_page(request):
    """
    Log users out and redirects them to the index.
    """
    logout(request)
    return redirect('/')


# Visualization views
@login_required
def visualize_json(request, handle_id):
    """
    Creates a JSON representation of the node and the adjacent nodes.
    This JSON data is then used by Arbor.js (http://arborjs.org/) to make
    a visual representation.
    """
    # Get the node
    nh = NodeHandle.objects.get(pk=handle_id)
    root_node = nc.get_node_model(nc.graphdb.manager, nh.handle_id)
    if root_node:
        # Create the data JSON structure needed
        graph_dict = arborgraph.create_generic_graph(root_node)
        jsonstr = arborgraph.get_json(graph_dict)
    else:
        jsonstr = '{}'
    return HttpResponse(jsonstr, content_type='application/json')


@login_required
def visualize(request, slug, handle_id):
    """
    Visualize view with JS that loads JSON data.
    """
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    node = nh.get_node()
    return render(request, 'noclook/visualize/visualize.html', {'node_handle': nh, 'node': node, 'slug': slug})


@login_required
def visualize_maximize(request, slug, handle_id):
    """
    Visualize view with JS that loads JSON data.
    """
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    node = nh.get_node()
    return render(request, 'noclook/visualize/visualize_maximize.html',
                              {'node_handle': nh, 'node': node, 'slug': slug})


# Search views
@login_required
def search(request, value='', form=None):
    """
    Search through nodes either from a POSTed search query or through an
    URL like /slug/key/value/ or /slug/value/.
    """
    result = []
    posted = False
    if request.POST:
        value = request.POST.get('q', '')
        posted = True
    if value:
        query = '(?i).*{}.*'.format(re_escape(value))
        # nodes = nc.search_nodes_by_value(nc.graphdb.manager, query)
        # TODO: when search uses the above go back to that
        q = """
            match (n:Node) where any(prop in keys(n) where n[prop] =~ {search}) return n
            """
        nodes = nc.query_to_list(nc.graphdb.manager, q, search=query)
        if form == 'csv':
            return helpers.dicts_to_csv_response([ n.properties for n in nodes])
        elif form == 'xls':
            return helpers.dicts_to_xls_response([ n.properties for n in nodes])
        for node in nodes:
            nh = get_object_or_404(NodeHandle, pk=node['n'].properties['handle_id'])
            item = {'node': node['n'].properties, 'nh': nh}
            result.append(item)
        if len(result) == 1:
            return redirect(result[0]['nh'].get_absolute_url())
    return render(request, 'noclook/search_result.html', {'value': value, 'result': result, 'posted': posted})


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
    response = HttpResponse(content_type='application/json')
    query = request.GET.get('query', None)
    if query:
        try:
            suggestions = []
            for node in nc.get_indexed_node(nc.graphdb.manager, 'name', query):
                suggestions.append(node['name'])
            d = {'query': query, 'suggestions': suggestions, 'data': []}
            json.dump(d, response)
        except Exception:
            pass
        return response
    return False


def neo4j_escape(_in):
    if type(_in) is list:
        return map(neo4j_escape, _in)
    return re_escape(_in).replace('\\', '\\\\')


@login_required
def search_port_typeahead(request):
    response = HttpResponse(content_type='application/json')
    to_find = request.GET.get('query', None)
    result = []
    if to_find:
        # split for search
        match_q = neo4j_escape(to_find.split())
        try:
            q = """
                MATCH (port:Port)<-[:Has]-(n:Node)
                OPTIONAL MATCH (n)-[:Located_in]->(n2:Node)
                OPTIONAL MATCH (n2)<-[:Has]-(s:Site)
                WITH port.handle_id as handle_id, 
                n.handle_id as parent_id,
                CASE WHEN n2 IS null THEN
                  ""
                WHEN s IS null THEN
                    n2.name + " "
                ELSE
                    s.name + " " + n2.name + " "
                END + n.name+" "+port.name as name
                WHERE name =~ '(?i).*{}.*'
                RETURN name, handle_id, parent_id
                """.format(".*".join(match_q))
            result = nc.query_to_list(nc.graphdb.manager, q)
        except Exception as e:
            raise e
    json.dump(result, response)
    return response


@login_required
def find_all(request, slug=None, key=None, value=None, form=None):
    """
    Search through nodes either from a POSTed search query or through an
    URL like /slug/key/value/, /slug/value/ /key/value/, /value/ or /key/.
    """
    label = None
    node_type = None
    if request.POST:
        value = request.POST.get('q', '')  # search for '' if blank
    if slug:
        try:
            node_type = get_object_or_404(NodeType, slug=slug)
            label = node_type.get_label()
        except Http404:
            return render(request, 'noclook/search_result.html',
                                      {'node_type': slug, 'key': key, 'value': value, 'result': None,
                                       'node_meta_type': None})
    if value:
        nodes = nc.search_nodes_by_value(nc.graphdb.manager, value, key, label)
    else:
        nodes = nc.get_nodes_by_type(nc.graphdb.manager, label)
    if form == 'csv':
        return helpers.dicts_to_csv_response(list(nodes))
    elif form == 'xls':
        return helpers.dicts_to_xls_response(list(nodes))
    result = []
    for node in nodes:
        nh = get_object_or_404(NodeHandle, pk=node['handle_id'])
        item = {'node': node, 'nh': nh}
        result.append(item)
    return render(request, 'noclook/search_result.html',
                              {'node_type': node_type, 'key': key, 'value': value, 'result': result})


# Google maps views
@login_required
def gmaps(request, slug):
    api_key = settings.GOOGLE_MAPS_API_KEY
    return render(request, 'noclook/google_maps.html', {'slug': slug, 'maps_api_key': api_key})


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
    sites = nc.get_nodes_by_type(nc.graphdb.manager, 'Site')
    site_list = []
    for site in sites:
        try:
            site = {
                'name': site['name'],
                'url': helpers.get_node_url(site['handle_id']),
                'lng': float(str(site.get('longitude', 0))),
                'lat': float(str(site.get('latitude', 0)))
            }
        except KeyError:
            continue
        site_list.append(site)
    response = HttpResponse(content_type='application/json')
    json.dump({'nodes': site_list, 'edges': []}, response)
    return response


@login_required
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
        MATCH (cable:Cable)
        WHERE cable.cable_type = "Dark Fiber"
        MATCH (cable)-[Connected_to]->(port)
        WITH cable, port
        MATCH (port)<-[:Has*0..]-(equipment)
        WHERE (equipment:Optical_Node) AND NOT equipment.type =~ "(?i).*tss.*"
        WITH cable, port, equipment
        MATCH p2=(equipment)-[:Located_in]->()<-[:Has*0..]-(loc)
        WHERE (loc:Site)
        RETURN cable, equipment, loc
        """
    result = nc.query_to_list(nc.graphdb.manager, q)
    nodes = {}
    edges = {}
    for item in result:
        node = {
            'name': item['equipment']['name'],
            'url': helpers.get_node_url(item['equipment']['handle_id']),
            'lng': float(str(item['loc'].get('longitude', 0))),
            'lat': float(str(item['loc'].get('latitude', 0)))
        }
        coords = {
            'lng': float(str(item['loc'].get('longitude', 0))),
            'lat': float(str(item['loc'].get('latitude', 0)))
        }
        edge = {
            'name': item['cable']['name'],
            'url': helpers.get_node_url(item['cable']['handle_id']),
            'end_points': [coords]
        }
        nodes[item['equipment']['name']] = node
        if item['cable']['name'] in edges:
            edges[item['cable']['name']]['end_points'].append(coords)
        else:
            edges[item['cable']['name']] = edge
    response = HttpResponse(content_type='application/json')
    json.dump({'nodes': nodes.values(), 'edges': edges.values()}, response)
    return response


@login_required
def qr_lookup(request, name):
    hits = list(nc.get_nodes_by_name(nc.graphdb.manager, name))
    if len(hits) == 1:
        nh = get_object_or_404(NodeHandle, pk=hits[0]['handle_id'])
        return redirect(nh.get_absolute_url())
    return render(request, 'noclook/qr_result.html', {'hits': hits, 'name': name})


@login_required
def ip_address_lookup(request):
    if request.POST:
        ip_address = request.POST.get('ip_address', None)
        if ip_address:
            hostname = helpers.get_hostname_from_address(ip_address)
            return HttpResponse(json.dumps(hostname), content_type='application/json')
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
            return helpers.dicts_to_csv_response(table, header)
        elif table and file_format == 'xls':
            return helpers.dicts_to_xls_response(table, header)
    raise Http404
