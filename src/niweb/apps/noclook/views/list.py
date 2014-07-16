# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from apps.noclook.models import NodeType
import apps.noclook.helpers as h
import norduniclient as nc


@login_required
def list_by_type(request, slug):
    node_type = get_object_or_404(NodeType, slug=slug)
    node_handle_list = node_type.nodehandle_set.all()
    return render_to_response('noclook/list/list_by_type.html',
                              {'node_handle_list': node_handle_list, 'node_type': node_type},
                              context_instance=RequestContext(request))


@login_required
def list_peering_partners(request):
    q = '''
        START node=node:node_types(node_type = "Peering Partner")
        MATCH node-[?:Uses]->peering_group
        WITH distinct node,peering_group
        RETURN node, collect(peering_group) as peering_groups
        ORDER BY node.name
        '''
    partner_list = nc.neo4jdb.query(q)
    return render_to_response('noclook/list/list_peering_partners.html', {'partner_list': partner_list},
                              context_instance=RequestContext(request))


@login_required
def list_hosts(request):
    q = '''
        MATCH (host:Host)
        OPTIONAL MATCH (host)<-[:Owns|Uses]-(user)
        RETURN host, collect(user) as users
        ORDER BY host.name
        '''
    with nc.neo4jdb.read as r:
        host_list = r.execute(q).fetchall()
    return render_to_response('noclook/list/list_hosts.html', {'host_list': host_list},
                              context_instance=RequestContext(request))


@login_required
def list_sites(request):
    node_types_index = nc.get_node_index(nc.neo4jdb, 'node_types')
    hits = node_types_index['node_type']['Site']
    site_list = []
    for node in hits:
        site = {
            'name': node['name']
        }
        try:
            site['country_code'] = node['country_code']
            site['country'] = node['country']
        except KeyError:
            site['country_code'] = ''
        site['site'] = node
        site_list.append(site)
    return render_to_response('noclook/list/list_sites.html', {'site_list': site_list},
                              context_instance=RequestContext(request))


@login_required
def list_services(request, service_class=None):
    if service_class:
        where_statement = 'WHERE node.service_class = "%s"' % service_class
    else:
        where_statement = ''
    q = '''
        START node=node:node_types(node_type = "Service")
        MATCH node<-[?:Uses]-user
        %s
        RETURN node, node.service_class? as service_class, node.service_type? as service_type,
        node.description? as description, node.operational_state? as operational_state, collect(user) as users
        ORDER BY node.name
        ''' % where_statement
    service_list = nc.neo4jdb.query(q)
    return render_to_response('noclook/list/list_services.html',
                              {'service_list': service_list, 'service_class': service_class},
                              context_instance=RequestContext(request))


@login_required
def list_optical_paths(request):
    q = '''
        START node=node:node_types(node_type = "Optical Path")
        RETURN node, node.framing? as framing, node.capacity? as capacity, node.enrs? as enrs,
        node.description? as description, node.operational_state? as operational_state
        '''
    optical_path_list = nc.neo4jdb.query(q)
    return render_to_response('noclook/list/list_optical_paths.html',
                              {'optical_path_list': optical_path_list},
                              context_instance=RequestContext(request))


@login_required
def list_optical_multiplex_section(request):
    q = '''
        START node=node:node_types(node_type = "Optical Multiplex Section")
        RETURN node
        '''
    hits = nc.neo4jdb.query(q)
    optical_multiplex_section_list = []
    for hit in hits:
        optical_multiplex_section = {
            'node': hit['node'],
            'optical_links': h.get_logical_depends_on(hit['node'])
        }
        optical_multiplex_section_list.append(optical_multiplex_section)
    return render_to_response('noclook/list/list_optical_multiplex_section.html',
                              {'optical_multiplex_section_list': optical_multiplex_section_list},
                              context_instance=RequestContext(request))


@login_required
def list_optical_links(request):
    q = '''
        START node=node:node_types(node_type = "Optical Link")
        RETURN node
        '''
    hits = nc.neo4jdb.query(q)
    optical_link_list = []
    for hit in hits:
        optical_link = {
            'node': hit['node'],
            'end_points': h.get_logical_depends_on(hit['node'])
        }
        optical_link_list.append(optical_link)
    return render_to_response('noclook/list/list_optical_links.html',
                              {'optical_link_list': optical_link_list},
                              context_instance=RequestContext(request))


@login_required
def list_routers(request):
    q = '''
        START node=node:node_types(node_type = "Router")
        RETURN node, node.model? as model, node.version? as version
        ORDER BY node.name
        '''
    router_list = nc.neo4jdb.query(q)
    return render_to_response('noclook/list/list_routers.html',
                              {'router_list': router_list},
                              context_instance=RequestContext(request))


@login_required
def list_optical_nodes(request):
    q = '''
        START node=node:node_types(node_type = "Optical Node")
        RETURN node, node.type? as type, node.link? as link, node.ots? as ots
        ORDER BY node.name
        '''
    optical_node_list = nc.neo4jdb.query(q)
    return render_to_response('noclook/list/list_optical_nodes.html',
                              {'optical_node_list': optical_node_list},
                              context_instance=RequestContext(request))


@login_required
def list_racks(request):
    q = '''
        START node=node:node_types(node_type = "Rack")
        MATCH node<-[?:Has]-site
        RETURN node,site
        ORDER BY site.name, node.name
        '''
    rack_list = nc.neo4jdb.query(q)
    return render_to_response('noclook/list/list_racks.html',
                              {'rack_list': rack_list},
                              context_instance=RequestContext(request))


@login_required
def list_odfs(request):
    q = '''
        START node=node:node_types(node_type = "ODF")
        MATCH node-[?:Located_in]->location<-[?:Has]-site
        RETURN node,location,site
        ORDER BY site.name, location.name, node.name
        '''
    odf_list = nc.neo4jdb.query(q)
    return render_to_response('noclook/list/list_odfs.html',
                              {'odf_list': odf_list},
                              context_instance=RequestContext(request))


@login_required
def list_cables(request):
    q = '''
        START cable=node:node_types(node_type = "Cable")
        RETURN cable
        ORDER BY cable.name
        '''
    cable_list = nc.neo4jdb.query(q)
    return render_to_response('noclook/list/list_cables.html',
                              {'cable_list': cable_list},
                              context_instance=RequestContext(request))