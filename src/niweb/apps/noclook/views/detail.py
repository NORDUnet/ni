# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
import ipaddress
import json
import logging

from apps.noclook.models import NodeHandle
from apps.noclook import helpers
from apps.noclook.views.helpers import Table, TableRow
import norduniclient as nc

logger = logging.getLogger(__name__)


@login_required
def generic_detail(request, handle_id, slug):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    # Get location
    location_path = node.get_location_path()
    return render(request, 'noclook/detail/detail.html',
                  {'node_handle': nh, 'node': node, 'slug': slug, 'location_path': location_path})


@login_required
def generic_history(request, handle_id, slug):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = helpers.get_history(nh)
    return render(request, 'noclook/detail/history.html',
                  {'node_handle': nh, 'history': history})


@login_required
def cable_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    cable = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(cable.data)

    # TODO: should be fixed in nc.get_connected_equipment
    q = """
                MATCH (n:Node {handle_id: {handle_id}})-[rel:Connected_to]->(port)
                OPTIONAL MATCH (port)<-[:Has*1..10]-(end)
                WITH  rel, port, last(collect(end)) as end
                OPTIONAL MATCH (end)-[:Located_in]->(location)
                OPTIONAL MATCH (location)<-[:Has*1..10]-(site:Site)
                RETURN id(rel) as rel_id, rel, port, end, location, site
                ORDER BY end.name, port.name
                """
    connections = nc.query_to_list(nc.graphdb.manager, q, handle_id=cable.handle_id)

    # connections = cable.get_connected_equipment()
    relations = cable.get_relations()
    dependent = cable.get_dependent_as_types()
    connection_path = cable.get_connection_path()
    urls = helpers.get_node_urls(cable, connections, relations, dependent)
    if not any(dependent.values()):
        dependent = None
    return render(request, 'noclook/detail/cable_detail.html',
                  {'node': cable, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                   'connections': connections, 'dependent': dependent, 'connection_path': connection_path,
                   'history': True, 'relations': relations, 'urls': urls})


@login_required
def customer_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    customer = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(customer.data)
    result = customer.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    # Handle relationships
    uses_relationships = customer.get_uses()
    owned_equipment = customer.get_owns()

    urls = helpers.get_node_urls(customer, same_name_relations, uses_relationships, owned_equipment)
    return render(
        request,
        'noclook/detail/customer_detail.html',
        {
            'node_handle': nh,
            'node': customer,
            'last_seen': last_seen,
            'expired': expired,
            'same_name_relations': same_name_relations,
            'uses_relationships': uses_relationships,
            'owned_equipment': owned_equipment,
            'history': True,
            'urls': urls,
        })


@login_required
def end_user_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    end_user = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(end_user.data)
    result = end_user.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    # Handle relationships
    uses_relationships = end_user.get_uses()
    return render(request, 'noclook/detail/end_user_detail.html',
                  {'node_handle': nh, 'node': end_user, 'last_seen': last_seen, 'expired': expired,
                   'same_name_relations': same_name_relations, 'uses_relationships': uses_relationships,
                   'history': True})


@login_required
def external_equipment_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    external_equipment = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(external_equipment.data)
    # Get ports in equipment
    connections = external_equipment.get_connections()
    # Get location
    location_path = external_equipment.get_location_path()
    # Get owner
    relations = external_equipment.get_relations()
    # Get dependents
    dependent = external_equipment.get_dependent_as_types()

    return render(
        request,
        'noclook/detail/external_equipment_detail.html',
        {
            'node': external_equipment,
            'node_handle': nh,
            'last_seen': last_seen,
            'expired': expired,
            'connections': connections,
            'relations': relations,
            'dependent': dependent,
            'location_path': location_path,
            'history': True})


@login_required
def firewall_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    firewall = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(firewall.data)
    location_path = firewall.get_location_path()
    # Get ports in firewall
    connections = firewall.get_connections()
    host_services = firewall.get_host_services()
    dependent = firewall.get_dependent_as_types()
    dependencies = firewall.get_dependencies_as_types()
    relations = firewall.get_relations()
    scan_enabled = helpers.app_enabled("apps.scan")
    return render(request, 'noclook/detail/firewall_detail.html',
                  {'node_handle': nh, 'node': firewall, 'last_seen': last_seen, 'expired': expired,
                   'host_services': host_services, 'connections': connections, 'dependent': dependent,
                   'dependencies': dependencies, 'relations': relations, 'location_path': location_path,
                   'history': True, 'scan_enabled': scan_enabled})


@login_required
def host_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    host = nc.get_node_model(nc.graphdb.manager, nh.handle_id)
    last_seen, expired = helpers.neo4j_data_age(host.data)
    location_path = host.get_location_path()
    # Handle relationships
    host_services = host.get_host_services()
    relations = host.get_relations()
    dependent = host.get_dependent_as_types()
    # Get ports in Host
    connections = host.get_connections()
    if not any(dependent.values()):
        dependent = None
    dependencies = host.get_dependencies_as_types()

    urls = helpers.get_node_urls(relations, host_services, dependent, dependencies)
    scan_enabled = helpers.app_enabled("apps.scan")
    return render(request, 'noclook/detail/host_detail.html',
                  {'node_handle': nh, 'node': host, 'last_seen': last_seen, 'expired': expired,
                   'relations': relations, 'host_services': host_services, 'dependent': dependent,
                   'dependencies': dependencies, 'location_path': location_path, 'history': True,
                   'urls': urls, 'connections': connections, 'scan_enabled': scan_enabled, })


@login_required
def host_provider_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    host_provider = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(host_provider.data)
    result = host_provider.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    provides_relationships = host_provider.get_provides()

    urls = helpers.get_node_urls(host_provider, same_name_relations, provides_relationships)
    return render(request, 'noclook/detail/host_provider_detail.html',
                  {'node_handle': nh, 'node': host_provider, 'last_seen': last_seen, 'expired': expired,
                   'same_name_relations': same_name_relations,
                   'provides_relationships': provides_relationships,
                   'history': True, 'urls': urls})


@login_required
def host_service_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    host_service = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(host_service.data)
    service_relationships = host_service.get_dependencies()

    urls = helpers.get_node_urls(host_service, service_relationships)
    return render(request, 'noclook/detail/host_service_detail.html',
                  {'node_handle': nh, 'node': host_service, 'last_seen': last_seen, 'expired': expired,
                   'service_relationships': service_relationships, 'history': True, 'urls': urls})


@login_required
def host_user_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    host_user = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(host_user.data)
    result = host_user.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    q = """
        MATCH (n:Node {handle_id: {handle_id}})-[r:Uses|:Owns]->(u)
        RETURN
        labels(u) as labels,
        u.handle_id as handle_id,
        u.name as name,
        u.noclook_last_seen as noclook_last_seen,
        u.noclook_auto_manage as noclook_auto_manage
        """
    host_relationships = nc.query_to_list(nc.graphdb.manager, q, handle_id=host_user.handle_id)

    urls = helpers.get_node_urls(host_user, same_name_relations, host_relationships)
    return render(request, 'noclook/detail/host_user_detail.html',
                  {'node_handle': nh, 'node': host_user, 'last_seen': last_seen, 'expired': expired,
                   'same_name_relations': same_name_relations, 'host_relationships': host_relationships,
                   'history': True, 'urls': urls},)


@login_required
def odf_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    odf = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(odf.data)
    # Get ports in ODF
    # connections = odf.get_connections()
    # TODO: should be fixed in nc.get_connections
    q = """
              MATCH (n:Node {handle_id: {handle_id}})-[:Has*1..10]->(porta:Port)
              OPTIONAL MATCH (porta)<-[r0:Connected_to]-(cable)
              OPTIONAL MATCH (cable)-[r1:Connected_to]->(portb:Port)
              WHERE ID(r1) <> ID(r0)
              OPTIONAL MATCH (portb)<-[:Has*1..10]-(end)
              WITH porta, r0, cable, portb, r1, last(collect(end)) as end
              OPTIONAL MATCH (end)-[:Located_in]->(location)
              OPTIONAL MATCH (location)<-[:Has*1..10]-(site:Site)
              RETURN porta, r0, cable, r1, portb, end, location, site
        """
    connections = nc.query_to_list(nc.graphdb.manager, q, handle_id=odf.handle_id)

    # Get location
    location_path = odf.get_location_path()

    urls = helpers.get_node_urls(odf, connections, location_path)
    return render(request, 'noclook/detail/odf_detail.html',
                  {'node': odf, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                   'connections': connections, 'location_path': location_path,
                   'history': True, 'urls': urls})

@login_required
def outlet_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    outlet = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(outlet.data)
    # Get ports in Patch Panel
    # connections = patch_panel.get_connections()
    # TODO: should be fixed in nc.get_connections
    q = """
              MATCH (n:Node {handle_id: {handle_id}})-[:Has*1..10]->(porta:Port)
              OPTIONAL MATCH (porta)<-[r0:Connected_to]-(cable)
              OPTIONAL MATCH (cable)-[r1:Connected_to]->(portb:Port)
              WHERE ID(r1) <> ID(r0)
              OPTIONAL MATCH (portb)<-[:Has*1..10]-(end)
              WITH porta, r0, cable, portb, r1, last(collect(end)) as end
              OPTIONAL MATCH (end)-[:Located_in]->(location)
              OPTIONAL MATCH (location)<-[:Has*1..10]-(site:Site)
              RETURN porta, r0, cable, r1, portb, end, location, site
        """
    connections = nc.query_to_list(nc.graphdb.manager, q, handle_id=outlet.handle_id)

    # Get location
    location_path = outlet.get_location_path()

    urls = helpers.get_node_urls(outlet, connections, location_path)
    return render(request, 'noclook/detail/outlet_detail.html',
                  {'node': outlet, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                   'connections': connections, 'location_path': location_path,
                   'history': True, 'urls': urls})


@login_required
def patch_panel_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    patch_panel = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(patch_panel.data)
    # Get ports in Patch Panel
    # connections = patch_panel.get_connections()
    # TODO: should be fixed in nc.get_connections
    q = """
              MATCH (n:Node {handle_id: {handle_id}})-[:Has*1..10]->(porta:Port)
              OPTIONAL MATCH (porta)<-[r0:Connected_to]-(cable)
              OPTIONAL MATCH (cable)-[r1:Connected_to]->(portb:Port)
              WHERE ID(r1) <> ID(r0)
              OPTIONAL MATCH (portb)<-[:Has*1..10]-(end)
              WITH porta, r0, cable, portb, r1, last(collect(end)) as end
              OPTIONAL MATCH (end)-[:Located_in]->(location)
              OPTIONAL MATCH (location)<-[:Has*1..10]-(site:Site)
              RETURN porta, r0, cable, r1, portb, end, location, site
        """
    connections = nc.query_to_list(nc.graphdb.manager, q, handle_id=patch_panel.handle_id)

    # Get location
    location_path = patch_panel.get_location_path()

    urls = helpers.get_node_urls(patch_panel, connections, location_path)
    return render(request, 'noclook/detail/patch_panel_detail.html',
                  {'node': patch_panel, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                   'connections': connections, 'location_path': location_path,
                   'history': True, 'urls': urls})


@login_required
def optical_filter_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    ofilter = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(ofilter.data)
    # Get ports in ODF
    connections = ofilter.get_connections()
    # Get location
    location_path = ofilter.get_location_path()

    urls = helpers.get_node_urls(ofilter, connections, location_path)
    return render(request, 'noclook/detail/optical_filter_detail.html',
                  {'node': ofilter, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                   'connections': connections, 'location_path': location_path,
                   'history': True, 'urls': urls})


@login_required
def optical_link_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    optical_link = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(optical_link.data)
    relations = optical_link.get_relations()
    dependent = optical_link.get_dependent_as_types()
    dependencies = optical_link.get_dependencies_as_types()
    return render(request, 'noclook/detail/optical_link_detail.html',
                  {'node': optical_link, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                   'dependent': dependent, 'dependencies': dependencies, 'relations': relations,
                   'history': True})


@login_required
def optical_multiplex_section_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    oms = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(oms.data)
    relations = oms.get_relations()
    dependent = oms.get_dependent_as_types()
    dependencies = oms.get_dependencies_as_types()

    urls = helpers.get_node_urls(oms, dependent, dependencies, relations)
    return render(request, 'noclook/detail/optical_multiplex_section_detail.html',
                  {'node': oms, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                   'dependent': dependent, 'dependencies': dependencies, 'relations': relations,
                   'history': True, 'urls': urls})


@login_required
def optical_node_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    optical_node = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(optical_node.data)
    location_path = optical_node.get_location_path()
    connections = optical_node.get_connections()
    dependent = optical_node.get_dependent_as_types()
    dependencies = optical_node.get_dependencies_as_types()

    urls = helpers.get_node_urls(optical_node, location_path, dependent, dependencies, connections)
    return render(request, 'noclook/detail/optical_node_detail.html',
                  {'node': optical_node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                   'location_path': location_path, 'dependent': dependent,
                   'dependencies': dependencies, 'connections': connections,
                   'history': True, 'urls': urls})


@login_required
def optical_path_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    optical_path = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(optical_path.data)
    relations = optical_path.get_relations()
    dependent = optical_path.get_dependent_as_types()
    dependencies = optical_path.get_dependencies_as_types()

    urls = helpers.get_node_urls(optical_path, dependent, dependencies, relations)
    return render(request, 'noclook/detail/optical_path_detail.html',
                  {'node': optical_path, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                   'dependencies': dependencies, 'dependent': dependent, 'relations': relations,
                   'history': True, 'urls': urls})


@login_required
def pdu_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    pdu = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(pdu.data)
    location_path = pdu.get_location_path()
    # Get ports in pdu
    connections = pdu.get_connections()
    host_services = pdu.get_host_services()
    dependent = pdu.get_dependent_as_types()
    dependencies = pdu.get_dependencies_as_types()
    relations = pdu.get_relations()

    urls = helpers.get_node_urls(pdu, host_services, connections, dependent, dependencies, relations, location_path)
    scan_enabled = helpers.app_enabled("apps.scan")
    return render(request, 'noclook/detail/pdu_detail.html',
                  {'node_handle': nh, 'node': pdu, 'last_seen': last_seen, 'expired': expired,
                   'host_services': host_services, 'connections': connections, 'dependent': dependent,
                   'dependencies': dependencies, 'relations': relations, 'location_path': location_path,
                   'history': True, 'urls': urls, 'scan_enabled': scan_enabled})


@login_required
def peering_group_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    peering_group = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(peering_group.data)
    # TODO: A better model for Peerings would be:
    # (unit)<-[:Depends_on]-(peering:Peering)<-[:Uses]-(partner:Peering_Partner)
    # (peering:Peering)-[:Depends_on]->(group:Peering_Group)
    user_dependencies = []
    dependencies = peering_group.get_dependencies()
    users = peering_group.get_relations().get('Uses', [])

    for item in dependencies.get('Depends_on', []):
        network_address = ipaddress.ip_network(item['relationship']['ip_address'], strict=False)
        interface = {
            'unit': item['node'],
            # calls neo4j but there are almost no dependencies normally
            'placement': item['node'].get_placement_path(),
            'network_address': u'{}'.format(network_address),
            'users': []
        }
        for user in users:
            user_address = ipaddress.ip_address(user['relationship']['ip_address'])
            if user_address in network_address:
                interface['users'].append({
                    'user': user['node'],
                    'user_address': u'{}'.format(user_address),
                    'relationship': user['relationship']
                })
        user_dependencies.append(interface)

    urls = helpers.get_node_urls(peering_group, user_dependencies)
    return render(request, 'noclook/detail/peering_group_detail.html',
                  {'node_handle': nh, 'node': peering_group, 'last_seen': last_seen, 'expired': expired,
                   'user_dependencies': user_dependencies,
                   'history': True, 'urls': urls})


@login_required
def peering_partner_detail(request, handle_id):
    # TODO: Needs to be rewritten using cypher
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    peering_partner = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(peering_partner.data)
    result = peering_partner.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    # TODO: A better model for Peerings would be:
    # (unit)<-[:Depends_on]-(peering:Peering)<-[:Uses]-(partner:Peering_Partner)
    # (peering:Peering)-[:Depends_on]->(group:Peering_Group)
    user_dependencies = []
    peering_groups = peering_partner.get_uses().get('Uses', [])
    # pruning groups...
    group_dependencies = {}
    for group in peering_groups:
        gnode = group['node']
        gnode_id = gnode.handle_id
        if not (gnode_id in group_dependencies):
            group_dependencies[gnode_id] = gnode.get_dependencies().get('Depends_on', [])

    for group in peering_groups:
        user_address = ipaddress.ip_address(group['relationship']['ip_address'])
        peering_group = {
            'peering_group': group['node'],
            'user_address': u'{}'.format(user_address),
        }
        for unit in group_dependencies[group['node'].handle_id]:
            network_address = ipaddress.ip_network(unit['relationship']['ip_address'], strict=False)
            if user_address in network_address:
                peering_group.update({
                    # TODO: warn: unit.get.placement_path called from view
                    'unit': unit['node'],
                    'network_address': u'{}'.format(network_address),
                    'relationship': unit['relationship']
                })
                break
        user_dependencies.append(peering_group)
    urls = helpers.get_node_urls(peering_partner, same_name_relations, user_dependencies)
    return render(request, 'noclook/detail/peering_partner_detail.html',
                  {'node_handle': nh, 'node': peering_partner, 'last_seen': last_seen, 'expired': expired,
                   'same_name_relations': same_name_relations, 'user_dependencies': user_dependencies,
                   'history': True, 'urls': urls})


@login_required
def port_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    port = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(port.data)
    location_path = port.get_location_path()
    connections = port.get_connections()
    dependent = port.get_dependent_as_types()
    connection_path = port.get_connection_path()
    # Units
    q = """
        MATCH (n:Node {handle_id: {handle_id}})<-[:Part_of]-(unit:Unit)
        RETURN unit
        """
    units = nc.query_to_list(nc.graphdb.manager, q, handle_id=port.handle_id)
    urls = helpers.get_node_urls(port, connections, dependent, location_path, units)
    return render(request, 'noclook/detail/port_detail.html', {
        'node': port,
        'node_handle': nh,
        'last_seen': last_seen,
        'expired': expired,
        'connections': connections,
        'dependent': dependent,
        'location_path': location_path,
        'connection_path': connection_path,
        'units': units,
        'history': True,
        'urls': urls
    })


@login_required
def provider_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    provider = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(provider.data)
    result = provider.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    # Handle relationships
    provides_relationships = provider.get_provides()

    urls = helpers.get_node_urls(provider, same_name_relations, provides_relationships)
    return render(request, 'noclook/detail/provider_detail.html',
                  {'node_handle': nh, 'node': provider, 'last_seen': last_seen, 'expired': expired,
                   'same_name_relations': same_name_relations,
                   'provides_relationships': provides_relationships,
                   'history': True, 'urls': urls})


def _nodes_without(nodes, what, excludes):
    return [n for n in nodes if n.get('node').data.get(what, '').lower() not in excludes]


@login_required
def rack_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    rack = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(rack.data)
    location_path = rack.get_location_path()
    # Get equipment in rack
    _located_in = rack.get_located_in().get('Located_in', [])
    physical_relationships = {
        "Located_in": _nodes_without(_located_in, 'operational_state', ['decommissioned'])
    }

    urls = helpers.get_node_urls(rack, physical_relationships, location_path)
    return render(request, 'noclook/detail/rack_detail.html',
                  {'node': rack, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                   'physical_relationships': physical_relationships, 'location_path': location_path,
                   'history': True, 'urls': urls})


def _zip_modules(chain, out):
    if chain:
        part = chain[0]
        name = part['name']
        out_part = next((p for p in out if p['name'] == name), None)
        if not out_part:
            out_part = part
            out_part['modules'] = []
            out.append(out_part)
        # process rest of chain
        _zip_modules(chain[1:], out_part['modules'])


@login_required
def router_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    router = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(router.data)
    location_path = router.get_location_path()
    # Get all the Ports and what depends on the port.
    connections = router.get_connections()
    dependent = router.get_dependent_as_types()

    hw_name = "{}-hardware.json".format(router.data.get('name', 'router'))
    hw_attachment = helpers.find_attachments(handle_id, hw_name).first()
    if hw_attachment:
        try:
            hardware_modules = [json.loads(helpers.attachment_content(hw_attachment))]
        except IOError as e:
            logger.warning('Missing hardware modules json for router %s(%s). Error was: %s', nh.node_name, nh.handle_id, e)
            hardware_modules = []
    else:
        hardware_modules = []

    # TODO: generally very inefficient lookups in view...
    urls = helpers.get_node_urls(router, location_path, dependent, connections, hardware_modules)
    return render(request, 'noclook/detail/router_detail.html',
                  {'node_handle': nh, 'node': router, 'last_seen': last_seen, 'expired': expired,
                   'location_path': location_path, 'dependent': dependent,
                   'connections': connections,
                   'hardware_modules': hardware_modules,
                   'history': True, 'urls': urls})


@login_required
def unit_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    unit = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(unit.data)
    location_path = unit.get_location_path()
    dependent = unit.get_dependent_as_types()
    dependencies = unit.get_dependencies_as_types()

    urls = helpers.get_node_urls(unit, dependent, dependencies, location_path)
    return render(request, 'noclook/detail/unit_detail.html',
                  {'node': unit, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                   'dependent': dependent, 'dependencies': dependencies, 'location_path': location_path,
                   'history': True, 'urls': urls})


@login_required
def service_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    service = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(service.data)
    relations = service.get_relations()
    dependent = service.get_dependent_as_types()
    dependencies = service.get_dependencies_as_types()

    urls = helpers.get_node_urls(service, dependent, dependencies, relations)
    return render(request, 'noclook/detail/service_detail.html',
                  {'node': service, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                   'dependent': dependent, 'dependencies': dependencies, 'relations': relations,
                   'history': True, 'urls': urls})


@login_required
def site_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    site = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(site.data)
    relations = site.get_relations()

    # Direct equipment (aka not racked)
    equipment_relationships = _nodes_without(site.get_located_in().get('Located_in', []), 'operational_state', ['decommissioned'])

    # Racked equipment
    q = """
    MATCH (site:Site {handle_id: {handle_id}})-[:Has]->(rack:Rack)
    OPTIONAL MATCH (rack)<-[:Located_in]-(item:Node)
    WHERE NOT item.operational_state IN ['Decommissioned'] OR NOT exists(item.operational_state)
    RETURN rack, item order by toLower(rack.name), toLower(item.name)
    """
    rack_list = nc.query_to_list(nc.graphdb.manager, q, handle_id=nh.handle_id)

    # Create racked equipment table
    racks_table = Table('Rack', 'Equipment')
    racks_table.rows = [TableRow(r.get('rack'), r.get('item')) for r in rack_list]

    # rooms
    q = """
        MATCH (site:Site {handle_id: {handle_id}})-[:Has]->(room:Room)
        RETURN room order by toLower(toString(room.name))
        """
    rooms_list = nc.query_to_list(nc.graphdb.manager, q, handle_id=nh.handle_id)

    rooms_table = Table('Rooms')
    rooms_table.rows = [TableRow(r.get('room')) for r in rooms_list]

    urls = helpers.get_node_urls(site, equipment_relationships, relations, rack_list, rooms_list)
    return render(request, 'noclook/detail/site_detail.html',
                  {'node_handle': nh,
                   'node': site,
                   'last_seen': last_seen,
                   'expired': expired,
                   'equipment_relationships': equipment_relationships,
                   'relations': relations,
                   'racks_table': racks_table,
                   'rooms_table': rooms_table,
                   'history': True,
                   'urls': urls,
                   'rack_list': rack_list,
                   })


@login_required
def room_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    room = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(room.data)
    relations = room.get_relations()

    # Direct equipment (aka not racked)
    equipment_relationships = _nodes_without(room.get_located_in().get('Located_in', []), 'operational_state', ['decommissioned'])

    # Racked equipment
    q = """
    MATCH (room:Room {handle_id: {handle_id}})-[:Has]->(rack:Node)
    OPTIONAL MATCH (rack)<-[:Located_in]-(item:Node)
    WHERE NOT item.operational_state IN ['Decommissioned'] OR NOT exists(item.operational_state)
    RETURN rack, item order by toLower(rack.name), toLower(item.name)
    """
    rack_list = nc.query_to_list(nc.graphdb.manager, q, handle_id=nh.handle_id)

    # Create racked equipment table
    racks_table = Table('Rack', 'Equipment')
    racks_table.rows = [TableRow(r.get('rack'), r.get('item')) for r in rack_list]

    location_path = room.get_location_path()

    urls = helpers.get_node_urls(room, equipment_relationships, relations, rack_list)
    return render(request, 'noclook/detail/room_detail.html',
                  {'node_handle': nh,
                   'node': room,
                   'last_seen': last_seen,
                   'expired': expired,
                   'equipment_relationships': equipment_relationships,
                   'relations': relations,
                   'racks_table': racks_table,
                   'history': True,
                   'urls': urls,
                   'location_path': location_path,
                   })


@login_required
def site_owner_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    site_owner = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(site_owner.data)
    result = site_owner.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    responsible_relations = site_owner.get_responsible_for()

    urls = helpers.get_node_urls(site_owner, same_name_relations, responsible_relations)
    return render(request, 'noclook/detail/site_owner_detail.html',
                  {'node_handle': nh, 'node': site_owner, 'last_seen': last_seen, 'expired': expired,
                   'same_name_relations': same_name_relations,
                   'responsible_relations': responsible_relations,
                   'history': True, 'urls': urls})


@login_required
def switch_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    switch = nh.get_node()
    last_seen, expired = helpers.neo4j_data_age(switch.data)
    location_path = switch.get_location_path()
    # Get ports in switch
    connections = switch.get_connections()
    host_services = switch.get_host_services()
    dependent = switch.get_dependent_as_types()
    dependencies = switch.get_dependencies_as_types()
    relations = switch.get_relations()

    urls = helpers.get_node_urls(switch, host_services, connections, dependent, dependencies, relations, location_path)
    scan_enabled = helpers.app_enabled("apps.scan")
    hw_name = "{}-hardware.json".format(switch.data.get('name', 'switch'))
    hw_attachment = helpers.find_attachments(handle_id, hw_name).first()
    if hw_attachment:
        try:
            hardware_modules = [json.loads(helpers.attachment_content(hw_attachment))]
        except IOError as e:
            logger.warning('Missing hardware modules json for router %s(%s). Error was: %s', nh.node_name, nh.handle_id, e)
            hardware_modules = []
    else:
        hardware_modules = []
    return render(request, 'noclook/detail/switch_detail.html',
                  {'node_handle': nh, 'node': switch, 'last_seen': last_seen, 'expired': expired,
                   'host_services': host_services, 'connections': connections, 'dependent': dependent,
                   'dependencies': dependencies, 'relations': relations, 'location_path': location_path,
                   'history': True, 'urls': urls, 'scan_enabled': scan_enabled, 'hardware_modules': hardware_modules})
