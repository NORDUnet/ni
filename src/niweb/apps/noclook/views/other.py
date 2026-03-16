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
        query = u'(?i).*{}.*'.format(re_escape(value))
        # nodes = nc.search_nodes_by_value(nc.graphdb.manager, query)
        # TODO: when search uses the above go back to that
        q = """
            match (n:Node) where any(prop in keys(n) where n[prop] =~ $search) return n
            """
        nodes = nc.query_to_list(nc.graphdb.manager, q, search=query)
        if form == 'csv':
            return helpers.dicts_to_csv_response([n['n'] for n in nodes])
        elif form == 'xls':
            return helpers.dicts_to_xls_response([n['n'] for n in nodes])
        for node in nodes:
            nh = get_object_or_404(NodeHandle, pk=node['n']['handle_id'])
            item = {'node': node['n'], 'nh': nh}
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


def regex_escape(_in):
    if type(_in) is list:
        return map(regex_escape, _in)
    return re_escape(_in)


@login_required
def search_port_typeahead(request):
    response = HttpResponse(content_type='application/json')
    to_find = request.GET.get('query', None)
    result = []
    if to_find:
        # split for search
        match_q = regex_escape(to_find.split())
        try:
            # TODO: check if size(nodes(p))/size(path) in neo4j>=4.4 is equivalent to length(nodes(p))/length(path) in neo4j==3.5
            q = """
                MATCH (port:Port)<-[:Has]-(n:Node)
                OPTIONAL MATCH (n)-[:Located_in]->(n2:Node)
                OPTIONAL MATCH p = () - [:Has * 0..20]->(n2)
                WITH COLLECT(nodes(p)) as paths, MAX(size(nodes(p))) AS maxLength,
                 port.handle_id AS handle_id, n.handle_id AS parent_id,
                 port.name AS port_name, n.name AS node_name
                WITH [path IN paths WHERE size(path) = maxLength] AS longestPaths,
                 handle_id AS handle_id, parent_id AS parent_id, port_name AS port_name, node_name AS node_name
                UNWIND(longestPaths) AS location_path
                WITH REDUCE(s = "", n IN location_path | s + n.name + " ") + node_name + " " + port_name AS name, handle_id, parent_id
                WHERE name =~ $name_re
                RETURN name, handle_id, parent_id
                """
            name_re = '(?i).*{}.*'.format('.*'.join(match_q))
            result = nc.query_to_list(nc.graphdb.manager, q, name_re=name_re)
        except Exception as e:
            raise e
    json.dump(result, response)
    return response


@login_required
def search_location_typeahead(request):
    response = HttpResponse(content_type='application/json')
    to_find = request.GET.get('query', None)
    result = []
    if to_find:
        # split for search
        match_q = regex_escape(to_find.split())
        try:
            # find all has relations to the top
            q = """
                MATCH p = (:Location) - [:Has * 0..20]-> (l:Location)
                WITH COLLECT(nodes(p)) as paths, MAX(size(nodes(p))) AS maxLength, l.handle_id as handle_id
                WITH [path IN paths WHERE size(path) = maxLength | path ] AS longestPaths, handle_id as handle_id
                UNWIND(longestPaths) AS location_path
                WITH REDUCE(s = "", n IN location_path | s + n.name + " ") AS name, handle_id
                WHERE name =~ $name_re
                RETURN name, handle_id
                """
            name_re = '(?i).*{}.*'.format('.*'.join(match_q))
            result = nc.query_to_list(nc.graphdb.manager, q, name_re=name_re)
        except Exception as e:
            raise e
    json.dump(result, response)
    return response


@login_required
def search_non_location_typeahead(request):
    response = HttpResponse(content_type='application/json')
    to_find = request.GET.get('query', None)
    result = []
    if to_find:
        # split for search
        match_q = regex_escape(to_find.split())
        try:
            q = """
                MATCH (n:Node)
                WHERE not n:Location
                OPTIONAL MATCH (n)<-[:Has]-(e:Node)
                WITH n.handle_id as handle_id,
                     coalesce(e.name, "") + " "+ n.name as name,
                     labels(n) as labels
                WHERE name =~ $name_re
                RETURN handle_id, trim(name) as name, labels ORDER BY name
                """
            name_re = '(?i).*{}.*'.format('.*'.join(match_q))

            result = nc.query_to_list(nc.graphdb.manager, q, name_re=name_re)
        except Exception as e:
            raise e
    for r in result:
        _type = [l for l in r['labels'] if l not in ['Node', 'Physical', 'Logical', 'Relation']]
        if _type:
            r['name'] = u'{} [{}]'.format(r['name'], _type[0])
    # TODO: do stuff with labels
    json.dump(result, response)
    return response


@login_required
def typeahead_slugs(request, slug='Node'):
    response = HttpResponse(content_type='application/json')
    to_find = request.GET.get('query', None)
    result = []
    if to_find:
        # split for search
        match_q = regex_escape(to_find.split())
        labels = [helpers.slug_to_node_type(s).get_label() for s in slug.split('+')]
        try:
            q = """
                MATCH (n:Node)
                WHERE any(label in labels(n) where label in $labels)
                OPTIONAL MATCH (n)<-[:Has]-(e:Node)
                WITH n.handle_id as handle_id,
                     coalesce(e.name, "") + " "+ n.name as name,
                     labels(n) as labels
                WHERE name =~ $name_re
                RETURN handle_id, trim(name) as name, labels ORDER BY name
                """
            name_re = '(?i).*{}.*'.format('.*'.join(match_q))
            result = nc.query_to_list(nc.graphdb.manager, q, labels=labels, name_re=name_re)
        except Exception as e:
            raise e
    if '+' in slug:
        for r in result:
            _type = [lab for lab in r['labels'] if lab not in ['Node', 'Physical', 'Logical', 'Relation']]
            if _type:
                r['name'] = u'{} [{}]'.format(r['name'], _type[0])

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
    Return a json object with dicts of optical nodes and optical links.
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
    # Cypher query to get all optical links that connect optical nodes
    q = """
        MATCH (link:Optical_Link)-[:Depends_on]->(port:Port)<-[:Has]-(equipment:Optical_Node)
        WITH link, equipment
        MATCH (equipment)-[:Located_in]->()<-[:Has*0..]-(loc)
        WHERE (loc:Site)
        RETURN link, equipment, loc
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
            'name': item['link']['name'],
            'url': helpers.get_node_url(item['link']['handle_id']),
            'end_points': [coords]
        }
        nodes[item['equipment']['name']] = node
        if item['link']['name'] in edges:
            edges[item['link']['name']]['end_points'].append(coords)
        else:
            edges[item['link']['name']] = edge
    response = HttpResponse(content_type='application/json')
    json.dump({'nodes': list(nodes.values()), 'edges': list(edges.values())}, response)
    return response


@login_required
def gmaps_optical_paths(request, node_handle_id):
    """
    Return optical paths that include the specified optical node.
    Returns JSON with path information and all the nodes in each path sequence.
    Only returns paths with operational_state = "In service".
    Includes paths where the node is an endpoint or a transit node.
    """
    q = """
        MATCH (node:Optical_Node)
        WHERE node.handle_id = $handle_id
        
        // Find all paths that pass through this node via optical links
        MATCH (node)-[:Has]->(port:Port)<-[:Depends_on]-(link:Optical_Link)
        <-[:Depends_on]-(oms:Optical_Multiplex_Section)<-[:Depends_on]-(path:Optical_Path)
        WHERE path.operational_state = "In service"
        
        WITH DISTINCT path
        
        // Get all nodes in each path
        MATCH (path)-[:Depends_on]->(oms:Optical_Multiplex_Section)
        -[:Depends_on]->(link:Optical_Link)
        -[:Depends_on]->(p:Port)<-[:Has]-(on:Optical_Node)
        WITH path, oms, link, on
        MATCH (on)-[:Located_in]->()<-[:Has*0..]-(loc:Site)
        WITH path, oms.name as oms_name, link.name as link_name, on, loc
        ORDER BY oms_name, link_name
        WITH path, collect({node: on, site: loc, oms: oms_name, link: link_name}) as all_nodes
        RETURN path, all_nodes
        """
    result = nc.query_to_list(nc.graphdb.manager, q, handle_id=int(node_handle_id))
    
    paths = []
    for item in result:
        # Build ordered path using graph traversal
        all_nodes_data = item['all_nodes']
        
        if not all_nodes_data:
            continue
        
        # Build adjacency graph from links
        # Each link connects exactly 2 nodes
        adjacency = {}  # node_id -> list of (neighbor_id, link_name)
        node_lookup = {}  # node_id -> node_data
        
        # Group nodes by link
        links_dict = {}
        for node_data in all_nodes_data:
            link_name = node_data['link']
            node_id = node_data['node']['handle_id']
            
            if link_name not in links_dict:
                links_dict[link_name] = []
            links_dict[link_name].append(node_data)
            node_lookup[node_id] = node_data
        
        # Build adjacency list
        for link_name, link_nodes in links_dict.items():
            if len(link_nodes) == 2:
                node1_id = link_nodes[0]['node']['handle_id']
                node2_id = link_nodes[1]['node']['handle_id']
                
                if node1_id not in adjacency:
                    adjacency[node1_id] = []
                if node2_id not in adjacency:
                    adjacency[node2_id] = []
                
                adjacency[node1_id].append((node2_id, link_name))
                adjacency[node2_id].append((node1_id, link_name))
        
        # Find path endpoints (nodes with only 1 connection) or start from any node
        endpoints = [nid for nid, neighbors in adjacency.items() if len(neighbors) == 1]
        
        if not endpoints:
            # No clear endpoints, start from first node
            start_node = list(adjacency.keys())[0] if adjacency else None
        else:
            # Start from one endpoint
            start_node = endpoints[0]
        
        if not start_node:
            continue
        
        # Traverse the path using DFS
        ordered_nodes = []
        visited = set()
        
        def dfs(node_id):
            if node_id in visited:
                return
            visited.add(node_id)
            ordered_nodes.append(node_lookup[node_id])
            
            # Visit unvisited neighbors
            if node_id in adjacency:
                for neighbor_id, _ in adjacency[node_id]:
                    if neighbor_id not in visited:
                        dfs(neighbor_id)
        
        dfs(start_node)
        
        path_nodes = []
        for node_data in ordered_nodes:
            path_nodes.append({
                'name': node_data['node']['name'],
                'handle_id': node_data['node']['handle_id'],
                'lng': float(str(node_data['site'].get('longitude', 0))),
                'lat': float(str(node_data['site'].get('latitude', 0)))
            })
        
        paths.append({
            'id': item['path']['handle_id'],
            'name': item['path']['name'],
            'description': item['path'].get('description', ''),
            'operational_state': item['path'].get('operational_state', ''),
            'nodes': path_nodes
        })
    
    response = HttpResponse(content_type='application/json')
    json.dump({'paths': paths}, response)
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
