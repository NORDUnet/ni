# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
import ipaddr

from apps.noclook.models import NodeHandle
import apps.noclook.helpers as h
import norduniclient as nc


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
    depend_out = h.iter2list(h.get_logical_depends_on(node))
    return render_to_response('noclook/detail/host_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'service_relationships': service_relationships, 'user_relationships': user_relationships,
                               'provider_relationships': provider_relationships, 'depend_out': depend_out,
                               'owner_relationships': owner_relationships, 'location': location, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def firewall_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    location = h.iter2list(h.get_location(node))
    # Handle relationships
    service_relationships = h.iter2list(node.Depends_on.incoming)
    owner_relationships = h.iter2list(node.Owns.incoming)
    return render_to_response('noclook/detail/firewall_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'service_relationships': service_relationships,
                               'owner_relationships': owner_relationships, 'location': location, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def switch_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(node)
    location = h.iter2list(h.get_location(node))
    # Get ports in switch
    connections = h.iter2list(h.get_connected_equipment(node))
    # Handle relationships
    service_relationships = h.iter2list(node.Depends_on.incoming)
    owner_relationships = h.iter2list(node.Owns.incoming)
    return render_to_response('noclook/detail/switch_detail.html',
                              {'node_handle': nh, 'node': node, 'last_seen': last_seen, 'expired': expired,
                               'service_relationships': service_relationships, 'connections': connections,
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


