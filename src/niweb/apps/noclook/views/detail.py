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
def cable_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    cable = nh.get_node()
    last_seen, expired = h.neo4j_data_age(cable.data)
    connections = cable.get_connected_equipment()
    relations = cable.get_relations()
    dependent = cable.get_dependent_as_types()
    if not any(dependent.values()):
        dependent = None
    return render_to_response('noclook/detail/cable_detail.html',
                              {'node': cable, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'connections': connections, 'dependent': dependent, 'history': history,
                               'relations': relations},
                              context_instance=RequestContext(request))


@login_required
def customer_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    customer = nh.get_node()
    last_seen, expired = h.neo4j_data_age(customer.data)
    result = customer.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    # Handle relationships
    uses_relationships = customer.get_uses()
    return render_to_response('noclook/detail/customer_detail.html',
                              {'node_handle': nh, 'node': customer, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations, 'uses_relationships': uses_relationships,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def end_user_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    end_user = nh.get_node()
    last_seen, expired = h.neo4j_data_age(end_user.data)
    result = end_user.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    # Handle relationships
    uses_relationships = end_user.get_uses()
    return render_to_response('noclook/detail/end_user_detail.html',
                              {'node_handle': nh, 'node': end_user, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations, 'uses_relationships': uses_relationships,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def external_equipment_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    external_equipment = nh.get_node()
    last_seen, expired = h.neo4j_data_age(external_equipment.data)
    # Get ports in equipment
    connections = external_equipment.get_connections()
    # Get location
    location_path = external_equipment.get_location_path()
    # Get owner
    relations = external_equipment.get_relations()
    return render_to_response('noclook/detail/external_equipment_detail.html',
                              {'node': external_equipment, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'connections': connections, 'relations': relations,
                               'location_path': location_path, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def firewall_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    firewall = nh.get_node()
    last_seen, expired = h.neo4j_data_age(switch.data)
    location_path = firewall.get_location_path()
    # Get ports in firewall
    connections = firewall.get_connections()
    host_services = firewall.get_host_services()
    dependent = firewall.get_dependent_as_types()
    dependencies = firewall.get_dependencies_as_types()
    relations = firewall.get_relations()
    return render_to_response('noclook/detail/firewall_detail.html',
                              {'node_handle': nh, 'node': firewall, 'last_seen': last_seen, 'expired': expired,
                               'host_services': host_services, 'connections': connections, 'dependent': dependent,
                               'dependencies': dependencies, 'relations': relations, 'location_path': location_path,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def host_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    host = nc.get_node_model(nc.neo4jdb, nh.handle_id)
    last_seen, expired = h.neo4j_data_age(host.data)
    location_path = host.get_location_path()
    # Handle relationships
    host_services = host.get_host_services()
    relations = host.get_relations()
    dependent = host.get_dependent_as_types()
    if not any(dependent.values()):
        dependent = None
    dependencies = host.get_dependencies_as_types()
    return render_to_response('noclook/detail/host_detail.html',
                              {'node_handle': nh, 'node': host, 'last_seen': last_seen, 'expired': expired,
                               'relations': relations, 'host_services': host_services, 'dependent': dependent,
                               'dependencies': dependencies, 'location_path': location_path, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def host_provider_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    host_provider = nh.get_node()
    last_seen, expired = h.neo4j_data_age(host_provider.data)
    result = host_provider.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    provides_relationships = host_provider.get_provides()
    return render_to_response('noclook/detail/host_provider_detail.html',
                              {'node_handle': nh, 'node': host_provider, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations,
                               'provides_relationships': provides_relationships, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def host_service_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    host_service = nh.get_node()
    last_seen, expired = h.neo4j_data_age(host_service.data)
    service_relationships = host_service.get_dependencies()
    return render_to_response('noclook/detail/host_service_detail.html',
                              {'node_handle': nh, 'node': host_service, 'last_seen': last_seen, 'expired': expired,
                               'service_relationships': service_relationships, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def host_user_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    host_user = nh.get_node()
    last_seen, expired = h.neo4j_data_age(host_user.data)
    result = host_user.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    host_relationships = host_user.get_uses()
    host_relationships.update(host_user.get_owns())
    return render_to_response('noclook/detail/host_user_detail.html',
                              {'node_handle': nh, 'node': host_user, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations, 'host_relationships': host_relationships,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def odf_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    odf = nh.get_node()
    last_seen, expired = h.neo4j_data_age(odf.data)
    # Get ports in ODF
    connections = odf.get_connections()
    # Get location
    location_path = odf.get_location_path()
    return render_to_response('noclook/detail/odf_detail.html',
                              {'node': odf, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'connections': connections, 'location_path': location_path, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def optical_link_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    optical_link = nh.get_node()
    last_seen, expired = h.neo4j_data_age(optical_link.data)
    relations = optical_link.get_relations()
    dependent = optical_link.get_dependent_as_types()
    dependencies = optical_link.get_dependencies_as_types()
    return render_to_response('noclook/detail/optical_link_detail.html',
                              {'node': optical_link, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'dependent': dependent, 'dependencies': dependencies, 'relations': relations,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def optical_multiplex_section_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    oms = nh.get_node()
    last_seen, expired = h.neo4j_data_age(oms.data)
    relations = oms.get_relations()
    dependent = oms.get_dependent_as_types()
    dependencies = oms.get_dependencies_as_types()
    return render_to_response('noclook/detail/optical_multiplex_section_detail.html',
                              {'node': oms, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'dependent': dependent, 'dependencies': dependencies, 'relations': relations,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def optical_node_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    optical_node = nh.get_node()
    last_seen, expired = h.neo4j_data_age(optical_node.data)
    location_path = optical_node.get_location_path()
    connections = optical_node.get_connections()
    dependent = optical_node.get_dependent_as_types()
    dependencies = optical_node.get_dependencies_as_types()
    return render_to_response('noclook/detail/optical_node_detail.html',
                              {'node': optical_node, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'location_path': location_path, 'history': history, 'dependent': dependent,
                               'dependencies': dependencies, 'connections': connections},
                              context_instance=RequestContext(request))


@login_required
def optical_path_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    optical_path = nh.get_node()
    last_seen, expired = h.neo4j_data_age(optical_path.data)
    relations = optical_path.get_relations()
    dependent = optical_path.get_dependent_as_types()
    dependencies = optical_path.get_dependencies_as_types()
    return render_to_response('noclook/detail/optical_path_detail.html',
                              {'node': optical_path, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'dependencies': dependencies, 'dependent': dependent, 'relations': relations,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def peering_group_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    peering_group = nh.get_node()
    last_seen, expired = h.neo4j_data_age(peering_group.data)
    # TODO: A better model for Peerings would be:
    # (unit)<-[:Depends_on]-(peering:Peering)<-[:Uses]-(partner:Peering_Partner)
    # (peering:Peering)-[:Depends_on]->(group:Peering_Group)
    user_dependencies = []
    dependencies = peering_group.get_dependencies()
    users = peering_group.get_relations().get('Uses', [])
    for item in dependencies.get('Depends_on', []):
        network_address = ipaddr.IPNetwork(item['relationship']['ip_address'])
        interface = {
            'unit': item['node'],
            'network_address': unicode(network_address),
            'users': []
        }
        for user in users:
            user_address = ipaddr.IPAddress(user['relationship']['ip_address'])
            if user_address in network_address:
                interface['users'].append({
                    'user': user['node'],
                    'user_address': unicode(user_address),
                    'relationship': user['relationship']
                })
        user_dependencies.append(interface)
    return render_to_response('noclook/detail/peering_group_detail.html',
                              {'node_handle': nh, 'node': peering_group, 'last_seen': last_seen, 'expired': expired,
                               'user_dependencies': user_dependencies, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def peering_partner_detail(request, handle_id):
    # TODO: Needs to be rewritten using cypher
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    peering_partner = nh.get_node()
    last_seen, expired = h.neo4j_data_age(peering_partner.data)
    result = peering_partner.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    # TODO: A better model for Peerings would be:
    # (unit)<-[:Depends_on]-(peering:Peering)<-[:Uses]-(partner:Peering_Partner)
    # (peering:Peering)-[:Depends_on]->(group:Peering_Group)
    user_dependencies = []
    peering_groups = peering_partner.get_uses().get('Uses', [])
    for group in peering_groups:
        user_address = ipaddr.IPAddress(group['relationship']['ip_address'])
        peering_group = {
            'peering_group': group['node'],
            'user_address': unicode(user_address),
        }
        for unit in group['node'].get_dependencies().get('Depends_on', []):
            network_address = ipaddr.IPNetwork(unit['relationship']['ip_address'])
            if user_address in network_address:
                peering_group.update({
                    'unit': unit['node'],
                    'network_address': unicode(network_address),
                    'relationship': unit['relationship']
                })
                break
        user_dependencies.append(peering_group)
    return render_to_response('noclook/detail/peering_partner_detail.html',
                              {'node_handle': nh, 'node': peering_partner, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations, 'user_dependencies': user_dependencies,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def port_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    port = nh.get_node()
    last_seen, expired = h.neo4j_data_age(port.data)
    location_path = port.get_location_path()
    connections = port.get_connections()
    dependent = port.get_dependent_as_types()
    return render_to_response('noclook/detail/port_detail.html',
                              {'node': port, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'connections': connections, 'dependent': dependent,
                               'location_path': location_path, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def provider_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    provider = nh.get_node()
    last_seen, expired = h.neo4j_data_age(provider.data)
    result = provider.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    # Handle relationships
    provides_relationships = provider.get_provides()
    return render_to_response('noclook/detail/provider_detail.html',
                              {'node_handle': nh, 'node': provider, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations,
                               'provides_relationships': provides_relationships, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def rack_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    rack = nh.get_node()
    last_seen, expired = h.neo4j_data_age(rack.data)
    location_path = rack.get_location_path()
    # Get equipment in rack
    physical_relationships = rack.get_located_in()
    return render_to_response('noclook/detail/rack_detail.html',
                              {'node': rack, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'physical_relationships': physical_relationships, 'location_path': location_path,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def router_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    router = nh.get_node()
    last_seen, expired = h.neo4j_data_age(router.data)
    location_path = router.get_location_path()
    # Get all the Ports and what depends on the port.
    connections = router.get_connections()
    dependent = router.get_dependent_as_types()
    return render_to_response('noclook/detail/router_detail.html',
                              {'node_handle': nh, 'node': router, 'last_seen': last_seen, 'expired': expired,
                               'location_path': location_path, 'history': history, 'dependent': dependent,
                               'connections': connections},
                              context_instance=RequestContext(request))


@login_required
def unit_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    unit = nh.get_node()
    last_seen, expired = h.neo4j_data_age(unit.data)
    location_path = unit.get_location_path()
    dependent = unit.get_dependent_as_types()
    dependencies = unit.get_dependencies_as_types()
    return render_to_response('noclook/detail/unit_detail.html',
                              {'node': unit, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'dependent': dependent, 'dependencies': dependencies, 'location_path': location_path,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def service_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    service = nh.get_node()
    last_seen, expired = h.neo4j_data_age(service.data)
    relations = service.get_relations()
    dependent = service.get_dependent_as_types()
    dependencies = service.get_dependencies_as_types()
    return render_to_response('noclook/detail/service_detail.html',
                              {'node': service, 'node_handle': nh, 'last_seen': last_seen, 'expired': expired,
                               'dependent': dependent, 'dependencies': dependencies, 'relations': relations,
                               'history': history},
                              context_instance=RequestContext(request))


@login_required
def site_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    site = nh.get_node()
    last_seen, expired = h.neo4j_data_age(site.data)
    relations = site.get_relations()
    equipment_relationships = site.get_located_in()
    location_relationships = site.get_has()
    return render_to_response('noclook/detail/site_detail.html',
                              {'node_handle': nh, 'node': site, 'last_seen': last_seen, 'expired': expired,
                               'equipment_relationships': equipment_relationships, 'relations': relations,
                               'location_relationships': location_relationships, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def site_owner_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    site_owner = nh.get_node()
    last_seen, expired = h.neo4j_data_age(site_owner.data)
    result = site_owner.with_same_name()
    same_name_relations = NodeHandle.objects.in_bulk((result.get('ids'))).values()
    responsible_relations = site_owner.get_responsible_for()
    return render_to_response('noclook/detail/site_owner_detail.html',
                              {'node_handle': nh, 'node': site_owner, 'last_seen': last_seen, 'expired': expired,
                               'same_name_relations': same_name_relations,
                               'responsible_relations': responsible_relations, 'history': history},
                              context_instance=RequestContext(request))


@login_required
def switch_detail(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    history = h.get_history(nh)
    # Get node from neo4j-database
    switch = nh.get_node()
    last_seen, expired = h.neo4j_data_age(switch.data)
    location_path = switch.get_location_path()
    # Get ports in switch
    connections = switch.get_connections()
    host_services = switch.get_host_services()
    dependent = switch.get_dependent_as_types()
    dependencies = switch.get_dependencies_as_types()
    relations = switch.get_relations()
    return render_to_response('noclook/detail/switch_detail.html',
                              {'node_handle': nh, 'node': switch, 'last_seen': last_seen, 'expired': expired,
                               'host_services': host_services, 'connections': connections, 'dependent': dependent,
                               'dependencies': dependencies, 'relations': relations, 'location_path': location_path,
                               'history': history},
                              context_instance=RequestContext(request))

