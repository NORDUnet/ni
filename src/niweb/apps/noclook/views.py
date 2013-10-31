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
    return render_to_response('noclook/index.html', {}, context_instance=RequestContext(request))


@login_required
def logout_page(request):
    """
    Log users out and redirects them to the index.
    """
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
        START host=node:node_types(node_type = "Host")
        MATCH host<-[?:Owns|Uses]-user
        RETURN host, host.name as name, host.os? as os, host.os_version? as os_version,
        host.ip_addresses? as ip_addresses, collect(user) as users
        ORDER BY host.name
        '''
    host_list = nc.neo4jdb.query(q)
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


# Detail views
@login_required
def generic_detail(request, handle_id, slug):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    return render_to_response('noclook/detail/detail.html',
                              {'node_handle': nh, 'node': node, 'slug': slug},
                              context_instance=RequestContext(request))


@login_required
def router_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    location = h.iter2list(h.get_location(node))
    # Get all the Ports and what depends on the port.
    loopback_addresses = []
    ports = []
    for hit in h.get_depends_on_router(node):
        port = {
            'port': hit['port'],
            'units': [],
            'depends_on_port': [],
        }
        for dep in hit['depends_on_port']:
            depends = None
            try:
                if dep['node_type'] == 'Unit':
                    port['units'].append(dep)
                    try:
                        for unit_dep in h.get_depends_on_unit(dep):
                            depends = {
                                'unit': dep,
                                'dep': unit_dep['depends_on_unit']
                            }
                    except TypeError:
                        pass
                else:
                    depends = {
                        'dep': dep
                    }
                if depends:
                    port['depends_on_port'].append(depends)
            except TypeError:
                pass
        ports.append(port)
    for address in loopback_addresses:
        try:
            ipaddr.IPNetwork(address)
        except ValueError:
            # Remove the ISO address
            loopback_addresses.remove(address)
    return render_to_response('noclook/detail/router_detail.html',
                              {'node_handle': nh, 'node': node, 'ports': ports, 'last_seen': last_seen,
                               'expired': expired, 'location': location, 'history': history,
                               'loopback_addresses': loopback_addresses},
                              context_instance=RequestContext(request))


@login_required
def optical_node_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    location = h.iter2list(h.get_location(node))
    #get incoming rels of fibers
    connected_rel = node.Connected_to.incoming  # Legacy
    depends_on = h.get_depends_on_equipment(node)
    services = h.iter2list(h.get_services_dependent_on_equipment(node))
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
    return render_to_response('noclook/detail/optical_node_detail.html',
                              {'node': node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'opt_info': opt_info, 'location': location, 'history': history, 'depends_on': depends_on,
                               'services': services},
                              context_instance=RequestContext(request))


@login_required
def host_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    location = h.iter2list(h.get_location(node))
    # Handle relationships
    service_relationships = h.iter2list(node.Depends_on.incoming)
    user_relationships = h.iter2list(node.Uses.incoming)
    provider_relationships = h.iter2list(node.Provides.incoming)
    owner_relationships = h.iter2list(node.Owns.incoming)
    return render_to_response('noclook/detail/host_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'service_relationships': service_relationships, 'user_relationships': user_relationships,
                               'provider_relationships': provider_relationships,
                               'owner_relationships': owner_relationships, 'location': location, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def host_service_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    service_relationships = h.iter2list(node.Depends_on.outgoing)
    return render_to_response('noclook/detail/host_service_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'service_relationships': service_relationships, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def host_provider_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    same_name_relations = h.iter2list(h.get_same_name_relations(node))
    host_relationships = h.iter2list(node.Provides.outgoing)
    return render_to_response('noclook/detail/host_provider_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations, 'host_relationships': host_relationships,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def host_user_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    same_name_relations = h.iter2list(h.get_same_name_relations(node))
    host_relationships = h.iter2list(node.Uses.outgoing) + h.iter2list(node.Owns.outgoing)
    return render_to_response('noclook/detail/host_user_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations, 'host_relationships': host_relationships,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def cable_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    connections = h.get_connected_cables(node)
    services = h.iter2list(h.get_services_dependent_on_cable(node))
    all_dependent = h.get_dependent_on_cable_as_types(node)
    return render_to_response('noclook/detail/cable_detail.html',
                              {'node': node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'connections': connections, 'services': services, 'all_dependent': all_dependent,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def peering_partner_detail(request, handle_id):
    # TODO: Needs to be rewritten using cypher
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    same_name_relations = h.iter2list(h.get_same_name_relations(node))
    # Get services used
    services_rel = node.Uses.outgoing
    # services_rel are relations to bgp groups(Service)
    peering_points = []
    for s_rel in services_rel:
        peering_point = {
            'pp_ip': s_rel['ip_address'],
            'service': s_rel.end['name'],
            'service_url': h.get_node_url(s_rel.end),
            's_rel': s_rel
        }
        unit_rels = s_rel.end.Depends_on.outgoing
        org_address = ipaddr.IPAddress(s_rel['ip_address'])
        for unit_rel in unit_rels:
            unit_address = ipaddr.IPNetwork(unit_rel['ip_address'])
            if org_address in unit_address:
                peering_point['if_address'] = unit_rel['ip_address']
                peering_point['unit'] = unit_rel.end['name']
                pic = unit_rel.end.Part_of.outgoing.single.end
                peering_point['pic'] = pic['name']
                peering_point['pic_url'] = h.get_node_url(pic)
                router = nc.get_root_parent(nc.neo4jdb, pic)[0]
                peering_point['router'] = router['name']
                peering_point['router_url'] = h.get_node_url(router)
                peering_points.append(peering_point)
    return render_to_response('noclook/detail/peering_partner_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations, 'peering_points': peering_points,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def peering_group_detail(request, handle_id):
    # TODO: Needs to be rewritten using cypher
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Get the units dependendant on
    unit_rels = node.Depends_on.outgoing
    service_resources = []
    for unit_rel in unit_rels:
        if_address = ipaddr.IPNetwork(unit_rel['ip_address'])
        interface = {
            'unit': unit_rel.end,
            'if_address': unit_rel['ip_address']
        }
        # TODO: If service depends on more than one PIC this won't show the correct information.
        try:
            pic = unit_rel.end.Part_of.outgoing.single.end
            router = nc.get_root_parent(nc.neo4jdb, pic)[0]
        except AttributeError:
            # Service does not depend on any interface
            pic = None
            router = None
        interface['pic'] = pic
        interface['router'] = router
        interface['relations'] = []
        # Get relations who uses the service
        rel_rels = node.Uses.incoming
        for r_rel in rel_rels:
            org_address = ipaddr.IPAddress(r_rel['ip_address'])
            if org_address in if_address:
                relation = {
                    'rel_address': r_rel['ip_address'],
                    'relation': r_rel.start,
                    'r_rel': r_rel
                }
                interface['relations'].append(relation)
        service_resources.append(interface)
    return render_to_response('noclook/detail/peering_group_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'service_resources': service_resources, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def site_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Handle relationships
    equipment_relationships = h.iter2list(node.Located_in.incoming)
    responsible_relationships = h.iter2list(node.Responsible_for.incoming)
    location_relationships = h.iter2list(h.get_racks_and_equipment(node))
    return render_to_response('noclook/detail/site_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'equipment_relationships': equipment_relationships,
                               'responsible_relationships': responsible_relationships,
                               'location_relationships': location_relationships, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def site_owner_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    same_name_relations = h.iter2list(h.get_same_name_relations(node))
    # Handle relationships
    site_relationships = h.iter2list(node.Responsible_for.outgoing)
    return render_to_response('noclook/detail/site_owner_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations, 'site_relationships': site_relationships,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def rack_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Get equipment in rack
    physical_relationships = h.iter2list(node.Located_in.incoming)
    # Get rack location
    location = h.iter2list(h.get_place(node))
    return render_to_response('noclook/detail/rack_detail.html',
                              {'node': node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'physical_relationships': physical_relationships, 'location': location,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def odf_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Get ports in ODF
    connections = h.iter2list(h.get_connected_equipment(node))
    # Get location
    location = h.iter2list(h.get_location(node))
    return render_to_response('noclook/detail/odf_detail.html',
                              {'node': node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'connections': connections, 'location': location, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def external_equipment_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Get ports in equipment
    connections = h.iter2list(h.get_connected_equipment(node))
    # Get location
    location = h.iter2list(h.get_location(node))
    # Get owner
    owner_relationships = h.iter2list(node.Owns.incoming)
    return render_to_response('noclook/detail/external_equipment_detail.html',
                              {'node': node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'connections': connections, 'owner_relationships': owner_relationships,
                               'location': location, 'history': history},
                              context_instance=RequestContext(request))

                              
@login_required
def port_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    # Get cables connected to the port
    connected_to_rels = h.iter2list(node.Connected_to.incoming)
    # Get things dependent on the port
    if connected_to_rels:
        depends_on_port = h.iter2list(h.get_depends_on_port(node))
    else:
        depends_on_port = h.iter2list(h.get_depends_on_equipment(node))

    # Get location
    location = h.iter2list(h.get_place(node))
    return render_to_response('noclook/detail/port_detail.html',
                              {'node': node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'connected_to_rels': connected_to_rels, 'depends_on_port': depends_on_port,
                               'location': location, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def unit_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    depend_inc = h.iter2list(node.Depends_on.incoming)
    depend_out = h.iter2list(h.get_logical_depends_on(node))
    part_of = h.iter2list(h.part_of(node))
    return render_to_response('noclook/detail/unit_detail.html',
                              {'node': node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'depend_inc': depend_inc, 'depend_out': depend_out, 'part_of': part_of,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def service_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    depend_in = h.iter2list(node.Depends_on.incoming)
    all_dependent = h.get_dependent_as_types(node)
    depend_out = h.iter2list(h.get_logical_depends_on(node))
    all_dependencies = h.get_dependencies_as_types(node)
    providers = h.iter2list(node.Provides.incoming)
    users = h.iter2list(node.Uses.incoming)
    return render_to_response('noclook/detail/service_detail.html',
                              {'node': node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'depend_in': depend_in, 'depend_out': depend_out, 'all_dependent': all_dependent,
                               'all_dependencies': all_dependencies, 'users': users, 'providers': providers,
                               'history': history}, context_instance=RequestContext(request))


@login_required
def optical_link_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    depend_in = h.iter2list(node.Depends_on.incoming)
    all_dependent = h.get_dependent_as_types(node)
    depend_out = h.iter2list(h.get_logical_depends_on(node))
    all_dependencies = h.get_dependencies_as_types(node)
    providers = h.iter2list(node.Provides.incoming)
    return render_to_response('noclook/detail/optical_link_detail.html',
                              {'node': node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'depend_in': depend_in, 'depend_out': depend_out, 'all_dependent': all_dependent,
                               'all_dependencies': all_dependencies, 'providers': providers, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def optical_multiplex_section_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    depend_in = h.iter2list(node.Depends_on.incoming)
    all_dependent = h.get_dependent_as_types(node)
    depend_out = h.iter2list(h.get_logical_depends_on(node))
    all_dependencies = h.get_dependencies_as_types(node)
    providers = h.iter2list(node.Provides.incoming)
    return render_to_response('noclook/detail/optical_multiplex_section_detail.html',
                              {'node': node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'depend_in': depend_in, 'depend_out': depend_out, 'all_dependent': all_dependent,
                               'all_dependencies': all_dependencies, 'providers': providers, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def optical_path_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    depend_in = h.iter2list(node.Depends_on.incoming)
    all_dependent = h.get_dependent_as_types(node)
    depend_out = h.iter2list(h.get_logical_depends_on(node))
    all_dependencies = h.get_dependencies_as_types(node)
    providers = h.iter2list(node.Provides.incoming)
    return render_to_response('noclook/detail/optical_path_detail.html',
                              {'node': node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'depend_in': depend_in, 'depend_out': depend_out, 'all_dependent': all_dependent,
                               'all_dependencies': all_dependencies, 'providers': providers, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def end_user_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    same_name_relations = h.iter2list(h.get_same_name_relations(node))
    # Handle relationships
    uses_relationships = h.iter2list(node.Uses.outgoing)
    return render_to_response('noclook/detail/end_user_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations, 'uses_relationships': uses_relationships,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def customer_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    same_name_relations = h.iter2list(h.get_same_name_relations(node))
    # Handle relationships
    uses_relationships = h.iter2list(node.Uses.outgoing)
    return render_to_response('noclook/detail/customer_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations, 'uses_relationships': uses_relationships,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def provider_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    same_name_relations = h.iter2list(h.get_same_name_relations(node))
    # Handle relationships
    provides_relationships = h.iter2list(node.Provides.outgoing)
    return render_to_response('noclook/detail/provider_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations,
                               'provides_relationships': provides_relationships, 'history': history},
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
