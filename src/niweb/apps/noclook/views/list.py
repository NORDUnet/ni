# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from apps.noclook.models import NodeType, NodeHandle
from apps.noclook.helpers import get_node_urls, find_recursive
import norduniclient as nc


@login_required
def list_by_type(request, slug):
    node_type = get_object_or_404(NodeType, slug=slug)
    q = """ 
        MATCH (node:%(nodetype)s)
        RETURN node
        ORDER BY node.name
        """ % {'nodetype': node_type.get_label()}
    node_list = nc.query_to_list(nc.neo4jdb, q)
    #Since all is the same type... we could use a defaultdict with type/id return
    urls = get_node_urls(node_list)
    return render_to_response('noclook/list/list_by_type.html',
                              {'node_list': node_list, 'node_type': node_type, 'urls': urls},
                              context_instance=RequestContext(request))


@login_required
def list_cables(request):
    q = """
        MATCH (cable:Cable)
        RETURN cable
        ORDER BY cable.name
        """
    cable_list = nc.query_to_list(nc.neo4jdb, q)
    urls = get_node_urls(cable_list)
    return render_to_response('noclook/list/list_cables.html',
                              {'cable_list': cable_list, 'urls': urls},
                              context_instance=RequestContext(request))


@login_required
def list_hosts(request):
    q = """
        MATCH (host:Host)
        OPTIONAL MATCH (host)<-[:Owns|Uses]-(user)
        RETURN host, collect(user) as users
        ORDER BY host.name
        """
    with nc.neo4jdb.read as r:
        host_list = r.execute(q).fetchall()
    urls = get_node_urls(host_list)
    return render_to_response('noclook/list/list_hosts.html', {'host_list': host_list, 'urls': urls},
                              context_instance=RequestContext(request))

@login_required
def list_switches(request):
    q = """
        MATCH (switch:Switch)
        OPTIONAL MATCH (switch)<-[:Owns|Uses]-(user)
        RETURN switch, collect(user) as users
        ORDER BY switch.name
        """
    with nc.neo4jdb.read as r:
        switch_list = r.execute(q).fetchall()
    urls = get_node_urls(switch_list)
    return render_to_response('noclook/list/list_switches.html', {'switch_list': switch_list, 'urls': urls},
                              context_instance=RequestContext(request))

@login_required
def list_odfs(request):
    q = """
        MATCH (odf:ODF)
        OPTIONAL MATCH (odf)-[:Located_in]->location
        OPTIONAL MATCH location<-[:Has]-site
        RETURN odf, location, site
        ORDER BY site.name, location.name, odf.name
        """
    odf_list = nc.query_to_list(nc.neo4jdb, q)
    urls = get_node_urls(odf_list)
    return render_to_response('noclook/list/list_odfs.html',
                              {'odf_list': odf_list, 'urls': urls},
                              context_instance=RequestContext(request))

@login_required
def list_optical_links(request):
    q = """
        MATCH (link:Optical_Link) 
        OPTIONAL MATCH (link)-[r:Depends_on]->(node)
        RETURN link as data, collect(node) as dependencies
        """
    optical_link_list = nc.query_to_list(nc.neo4jdb, q)

    q = """
        MATCH (n:Node)<-[:Has]-(parent)
        WHERE n.handle_id in {handle_ids}            
        RETURN  n.handle_id, parent
        """
    handle_ids = [ hid for link in optical_link_list for hid in find_recursive("handle_id", link.get('dependencies', [])) ]
    placement_paths_raw = nc.query_to_list(nc.neo4jdb, q, handle_ids=handle_ids)
    
    placement_paths = { p.get("n.handle_id"): p.get("parent") for p in placement_paths_raw }
    
    for link in optical_link_list:
      for dependency in link.get("dependencies", []):
        dependency.update({"placement_path": placement_paths.get(dependency.get("handle_id"))})

    urls = get_node_urls(optical_link_list)
    return render_to_response('noclook/list/list_optical_links.html',
                              {'optical_link_list': optical_link_list, 'urls': urls},
                              context_instance=RequestContext(request))


@login_required
def list_optical_multiplex_section(request):
    q = """
        MATCH (oms:Optical_Multiplex_Section)
        RETURN collect(oms.handle_id) as ids
        """
    result = nc.query_to_dict(nc.neo4jdb, q)
    optical_multiplex_section_list = []
    for handle_id in result['ids']:
        optical_multiplex_section_list.append(nc.get_node_model(nc.neo4jdb, handle_id))
    #TODO: template looks up dependencies... is that correct?
    urls = get_node_urls(optical_multiplex_section_list)
    return render_to_response('noclook/list/list_optical_multiplex_section.html',
                              {'optical_multiplex_section_list': optical_multiplex_section_list, 'urls': urls},
                              context_instance=RequestContext(request))

@login_required
def list_optical_nodes(request):
    q = """
        MATCH (node:Optical_Node)
        RETURN node, node.type as type, node.link as link, node.ots as ots
        ORDER BY node.name
        """
    optical_node_list = nc.query_to_list(nc.neo4jdb, q)
    urls = get_node_urls(optical_node_list)
    return render_to_response('noclook/list/list_optical_nodes.html',
                              {'optical_node_list': optical_node_list, 'urls': urls},
                              context_instance=RequestContext(request))


@login_required
def list_optical_paths(request):
    q = """
        MATCH (path:Optical_Path)
        RETURN path, path.framing as framing, path.capacity as capacity, path.enrs as enrs,
            path.description as description, path.operational_state as operational_state
        ORDER BY path.name
        """
    optical_path_list = nc.query_to_list(nc.neo4jdb, q)
    urls = get_node_urls(optical_path_list)
    return render_to_response('noclook/list/list_optical_paths.html',
                              {'optical_path_list': optical_path_list, 'urls': urls},
                              context_instance=RequestContext(request))


@login_required
def list_peering_partners(request):
    q = """
        MATCH (peer:Peering_Partner)
        OPTIONAL MATCH peer-[:Uses]->peering_group
        WITH distinct peer, peering_group
        RETURN peer, collect(peering_group) as peering_groups
        ORDER BY peer.name
        """
    partner_list = nc.query_to_list(nc.neo4jdb, q)
    urls = get_node_urls(partner_list)
    return render_to_response('noclook/list/list_peering_partners.html', 
                              {'partner_list': partner_list, 'urls': urls},
                              context_instance=RequestContext(request))


@login_required
def list_racks(request):
    q = """
        MATCH (rack:Rack)
        OPTIONAL MATCH rack<-[:Has]-site
        RETURN rack, site
        ORDER BY site.name, rack.name
        """
    rack_list = nc.query_to_list(nc.neo4jdb, q)
    urls = get_node_urls(rack_list)
    return render_to_response('noclook/list/list_racks.html',
                              {'rack_list': rack_list, 'urls':urls},
                              context_instance=RequestContext(request))


@login_required
def list_routers(request):
    q = """
        MATCH (router:Router)
        RETURN router, router.model as model, router.version as version, router.operational_state as operational_state
        ORDER BY router.name
        """
    router_list = nc.query_to_list(nc.neo4jdb, q)
    urls = get_node_urls(router_list)
    return render_to_response('noclook/list/list_routers.html',
                              {'router_list': router_list, 'urls':urls},
                              context_instance=RequestContext(request))


@login_required
def list_services(request, service_class=None):
    where_statement = ''
    if service_class:
        where_statement = 'WHERE service.service_class = "%s"' % service_class
    q = """
        MATCH (service:Service)
        %s
        OPTIONAL MATCH (service)<-[:Uses]-(customer:Customer)
        WITH service, COLLECT(customer) as customers
        OPTIONAL MATCH (service)<-[:Uses]-(end_user:End_User)
        RETURN service, service.service_class as service_class,
            service.service_type as service_type, service.description as description,
            customers, COLLECT(end_user) as end_users
        ORDER BY service.name
        """ % where_statement
    service_list = nc.query_to_list(nc.neo4jdb, q)
    urls = get_node_urls(service_list)
    return render_to_response('noclook/list/list_services.html',
                              {'service_list': service_list, 'service_class': service_class, 'urls': urls},
                              context_instance=RequestContext(request))


@login_required
def list_sites(request):
    q = """
        MATCH (site:Site)
        RETURN site
        ORDER BY site.country_code, site.name
        """
    site_list = nc.query_to_list(nc.neo4jdb, q)
    urls = get_node_urls(site_list)
    return render_to_response('noclook/list/list_sites.html', {'site_list': site_list, 'urls': urls},
                              context_instance=RequestContext(request))








