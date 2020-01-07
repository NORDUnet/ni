# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.noclook.models import NodeType, NodeHandle
from apps.noclook.views.helpers import Table, TableRow
from apps.noclook.helpers import get_node_urls, neo4j_data_age
import norduniclient as nc

__author__ = 'lundberg'

OPERATIONAL_BADGES = [
    ('badge-info', 'Testing'),
    ('badge-warning', 'Reserved'),
    ('badge-important', 'Decommissioned'),
]


def is_expired(node):
    last_seen, expired = neo4j_data_age(node)
    return expired


def _set_expired(row, node):
    if is_expired(node):
        row.classes = 'expired'


def _set_operational_state(row, node):
    if node.get('operational_state'):
        row.classes = node.get('operational_state').lower()


def _set_filters_expired(table, request):
    table.add_filter('', 'Current', 'hide_current', request.GET.copy())
    table.add_filter('badge-important', 'Expired', 'show_expired', request.GET.copy())


def _set_filters_operational_state(table, request):
    table.add_filter('', 'In service', 'hide_in_service', request.GET.copy())
    table.add_filter('badge-info', 'Testing', 'show_testing', request.GET.copy())
    table.add_filter('badge-warning', 'Reserved', 'show_reserved', request.GET.copy())
    table.add_filter('badge-important', 'Decommissioned', 'show_decommissioned', request.GET.copy())


def any_filter(filters, n):
    return any([f(n) for f in filters])


def all_filters(filters, n):
    return all([f(n) for f in filters])


def _filter_expired(nodes, request, select=lambda n: n):
    filters = []
    if 'show_expired' in request.GET:
        filters.append(lambda n: is_expired(n))
    if 'hide_current' not in request.GET:
        filters.append(lambda n: not is_expired(n))
    return [n for n in nodes if any_filter(filters, select(n))]


def _filter_operational_state(nodes, request, select=lambda n: n):
    exclude = []
    if 'show_testing' not in request.GET:
        exclude.append('testing')
    if 'show_reserved' not in request.GET:
        exclude.append('reserved')
    if 'show_decommissioned' not in request.GET:
        exclude.append('decommissioned')
    if 'hide_in_service' in request.GET:
        exclude.append('in service')
    return [n for n in nodes if select(n).get('operational_state', '').lower() not in exclude]


def _type_table(wrapped_node):
    node = wrapped_node.get('node')
    row = TableRow(node, node.get('description'))
    _set_expired(row, node)
    return row


@login_required
def list_by_type(request, slug):
    node_type = get_object_or_404(NodeType, slug=slug)
    q = """
        MATCH (node:%(nodetype)s)
        RETURN node
        ORDER BY node.name
        """ % {'nodetype': node_type.get_label()}
    node_list = nc.query_to_list(nc.graphdb.manager, q)
    node_list = _filter_expired(node_list, request, select=lambda n: n.get('node'))
    # Since all is the same type... we could use a defaultdict with type/id return
    urls = get_node_urls(node_list)

    table = Table('Name', 'Description')
    table.rows = [_type_table(node) for node in node_list]
    _set_filters_expired(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': '{}s'.format(node_type), 'urls': urls})


def _cable_end(end):
    equpment = end.get('equipment') or ''
    port_name = end.get('port') or ''
    return {
        'name': '{} - {}'.format(equpment, port_name),
        'handle_id': end.get('handle_id')
    }


def _cable_table(wrapped_cable):
    cable = wrapped_cable.get('cable')
    equipment = [e.get('equipment') for e in wrapped_cable.get('end') if e.get('equipment').get('handle_id')]
    ports = [e.get('port') for e in wrapped_cable.get('end') if e.get('port').get('handle_id')]
    row = TableRow(cable, cable.get('cable_type'), equipment, ports)
    _set_expired(row, cable)
    return row


@login_required
def list_cables(request):
    # MK: not 100% sure this gives the correct end+port pairs
    # Due to the <-[:Has*1..10]
    q = """
        MATCH (cable:Cable)
        OPTIONAL MATCH (cable)-[r:Connected_to]->(port:Port)
        OPTIONAL MATCH (port)<-[:Has*1..10]-(end)
        WHERE NOT((end)<-[:Has]-())
        RETURN cable, collect({equipment: {name: end.name, handle_id: end.handle_id}, port: {name: port.name, handle_id: port.handle_id}}) as end order by cable.name
        """
    cable_list = nc.query_to_list(nc.graphdb.manager, q)
    cable_list = _filter_expired(cable_list, request, select=lambda n: n.get('cable'))
    urls = get_node_urls(cable_list)

    table = Table('Name', 'Cable type', 'End equipment', 'Port')
    table.rows = [_cable_table(item) for item in cable_list]
    _set_filters_expired(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Cables', 'urls': urls})


def _port_row(wrapped_port):
    port = wrapped_port.get('port')
    parent = wrapped_port.get('parent')
    row = TableRow(port, port.get('description'), parent)
    _set_expired(row, port)
    return row


@login_required
def list_ports(request):
    q = """
        MATCH (port:Port)
        OPTIONAL MATCH (port)<-[:Has]-(parent:Node)
        RETURN port, collect(parent) as parent order by toLower(port.name)
        """
    port_list = nc.query_to_list(nc.graphdb.manager, q)
    port_list = _filter_expired(port_list, request, select=lambda n: n.get('port'))
    urls = get_node_urls(port_list)

    table = Table('Name', 'Description', 'Equipment')
    table.rows = [_port_row(item) for item in port_list]
    _set_filters_expired(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Ports', 'urls': urls})


def _customer_table(wrapped_customer):
    customer = wrapped_customer.get('customer')
    return TableRow(customer, customer.get('description'))


@login_required
def list_customers(request):
    q = """
        MATCH (customer:Customer)
        RETURN customer
        ORDER BY customer.name
        """
    customer_list = nc.query_to_list(nc.graphdb.manager, q)
    urls = get_node_urls(customer_list)

    table = Table('Name', 'Description')
    table.rows = [_customer_table(customer) for customer in customer_list]
    table.no_badges = True

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Customers', 'urls': urls})


def _host_table(host, users):
    ip_addresses = host.get('ip_addresses', ['No address'])
    os = host.get('os')
    os_version = host.get('os_version')
    row = TableRow(host, ip_addresses, os, os_version, users)
    _set_expired(row, host)
    _set_operational_state(row, host)
    return row


@login_required
def list_hosts(request):
    q = """
        MATCH (host:Host)
        OPTIONAL MATCH (host)<-[:Owns|Uses]-(user)
        RETURN host, collect(user) as users
        ORDER BY host.name
        """

    host_list = nc.query_to_list(nc.graphdb.manager, q)
    host_list = _filter_expired(host_list, request, select=lambda n: n.get('host'))
    host_list = _filter_operational_state(host_list, request, select=lambda n: n.get('host'))
    urls = get_node_urls(host_list)

    table = Table('Host', 'Address', 'OS', 'OS version', 'User')
    table.rows = [_host_table(item['host'], item['users']) for item in host_list]
    _set_filters_expired(table, request)
    _set_filters_operational_state(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Hosts', 'urls': urls})


def _switch_table(switch, users):
    ip_addresses = switch.get('ip_addresses', ['No address'])
    model = switch.get('model')
    row = TableRow(switch, model, ip_addresses, users)
    _set_expired(row, switch)
    return row


@login_required
def list_switches(request):
    q = """
        MATCH (switch:Switch)
        OPTIONAL MATCH (switch)<-[:Owns|Uses]-(user)
        RETURN switch, collect(user) as users
        ORDER BY switch.name
        """

    switch_list = nc.query_to_list(nc.graphdb.manager, q)
    switch_list = _filter_expired(switch_list, request, select=lambda n: n.get('switch'))
    urls = get_node_urls(switch_list)

    table = Table('Switch', 'Model', 'Address', 'User')
    table.rows = [_switch_table(item['switch'], item['users']) for item in switch_list]
    _set_filters_expired(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'name': 'Switches', 'table': table, 'urls': urls})


@login_required
def list_firewalls(request):
    q = """
        MATCH (firewall:Firewall)
        OPTIONAL MATCH (firewall)<-[:Owns|Uses]-(user)
        RETURN firewall, collect(user) as users
        ORDER BY firewall.name
        """

    firewall_list = nc.query_to_list(nc.graphdb.manager, q)
    firewall_list = _filter_expired(firewall_list, request, select=lambda n: n.get('firewall'))
    urls = get_node_urls(firewall_list)

    table = Table('Firewall', 'Model', 'Address', 'User')
    table.rows = [_switch_table(item['firewall'], item['users']) for item in firewall_list]
    _set_filters_expired(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'name': 'Firewalls', 'table': table, 'urls': urls})


def _odf_table(item):
    odf = item.get('odf')
    location_path = item.get('location_path')

    row = TableRow(odf, location_path)
    _set_operational_state(row, odf)
    return row


@login_required
def list_odfs(request):
    q = """
        MATCH (odf:ODF)
        OPTIONAL MATCH (odf)-[:Located_in]->(r)
        OPTIONAL MATCH p=()-[:Has*0..20]->(r)
        WITH COLLECT(nodes(p)) as paths, MAX(length(nodes(p))) AS maxLength, odf
        WITH FILTER(path IN paths WHERE length(path)=maxLength) AS longestPaths, odf AS odf
        UNWIND CASE WHEN longestPaths = [] THEN [null] ELSE longestPaths END as location_path
        RETURN odf, location_path
        ORDER BY odf.name
        """
    odf_list = nc.query_to_list(nc.graphdb.manager, q)
    odf_list = _filter_operational_state(odf_list, request, select=lambda n: n.get('odf'))
    urls = get_node_urls(odf_list)


    table = Table("Name", "Location")
    table.rows = [_odf_table(item) for item in odf_list]
    # Filter out
    _set_filters_operational_state(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'ODFs', 'urls': urls})

def _outlet_table(item):
    outlet = item.get('outlet')
    location_path = item.get('location_path')

    row = TableRow(outlet, location_path)
    _set_operational_state(row, outlet)
    return row


@login_required
def list_outlet(request):
    q = """
        MATCH (outlet:Outlet)
        OPTIONAL MATCH (outlet)-[:Located_in]->(r)
        OPTIONAL MATCH p=()-[:Has*0..20]->(r)
        WITH COLLECT(nodes(p)) as paths, MAX(length(nodes(p))) AS maxLength, outlet
        WITH FILTER(path IN paths WHERE length(path)=maxLength) AS longestPaths, outlet
        UNWIND CASE WHEN longestPaths = [] THEN [null] ELSE longestPaths END as location_path
        RETURN outlet, location_path
        ORDER BY outlet.name
        """
    outlet_list = nc.query_to_list(nc.graphdb.manager, q)
    outlet_list = _filter_operational_state(outlet_list, request, select=lambda n: n.get('outlet'))
    urls = get_node_urls(outlet_list)


    table = Table("Name", "Location" )
    table.rows = [_outlet_table(item) for item in outlet_list]
    # Filter out
    _set_filters_operational_state(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Outlets', 'urls': urls})


def _patch_panel_table(item):
    patch_panel = item.get('patch_panel')
    location_path = item.get('location_path')

    row = TableRow(patch_panel, location_path)
    _set_operational_state(row, patch_panel)
    return row


@login_required
def list_patch_panels(request):
    q = """
        MATCH (patch_panel:Patch_Panel)
        OPTIONAL MATCH (patch_panel)-[:Located_in]->(r)
        OPTIONAL MATCH p=()-[:Has*0..20]->(r)
        WITH COLLECT(nodes(p)) as paths, MAX(length(nodes(p))) AS maxLength, patch_panel
        WITH FILTER(path IN paths WHERE length(path)=maxLength) AS longestPaths, patch_panel AS patch_panel
        UNWIND CASE WHEN longestPaths = [] THEN [null] ELSE longestPaths END as location_path
        RETURN patch_panel, location_path
        ORDER BY patch_panel.name
        """
    patch_panel_list = nc.query_to_list(nc.graphdb.manager, q)
    patch_panel_list = _filter_operational_state(patch_panel_list, request, select=lambda n: n.get('patch_panel'))
    urls = get_node_urls(patch_panel_list)


    table = Table("Name", "Location" )
    table.rows = [_patch_panel_table(item) for item in patch_panel_list]
    # Filter out
    _set_filters_operational_state(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Patch Panels', 'urls': urls})


def _optical_link_table(link, dependencies):
    dependencies_view = []
    for deps in dependencies:
        if deps[0] is None:
            continue
        node = {'name': deps[0], 'handle_id': deps[0]['handle_id']}
        if node and len(deps) > 1:
            name = [n.get('name') for n in reversed(deps) if n]
            node['name'] = u' '.join(name)
        dependencies_view.append(node)
    row = TableRow(link, link.get('link_type'), link.get('description'), dependencies_view)
    _set_operational_state(row, link)
    return row


@login_required
def list_optical_links(request):
    # TODO: returns [None,None] and [node, None]
    #   tried to use [:Has *0-1] path matching but that gave "duplicate paths"
    q = """
        MATCH (link:Optical_Link)
        OPTIONAL MATCH (link)-[:Depends_on]->(node)
        OPTIONAL MATCH p=(node)<-[:Has]-(parent)
        RETURN link as link, collect([node, parent]) as dependencies
        """
    optical_link_list = nc.query_to_list(nc.graphdb.manager, q)
    optical_link_list = _filter_operational_state(optical_link_list, request, select=lambda n: n.get('link'))
    table = Table('Optical Link', 'Type', 'Description', 'Depends on')
    table.rows = [_optical_link_table(item['link'], item['dependencies']) for item in optical_link_list]
    _set_filters_operational_state(table, request)

    urls = get_node_urls(optical_link_list)
    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Optical Links', 'urls': urls})


def _oms_table(oms, dependencies):
    row = TableRow(oms, oms.get('description'), dependencies)
    if oms.get('operational_state'):
        row.classes = oms.get('operational_state').lower()
    return row


@login_required
def list_optical_multiplex_section(request):
    q = """
        MATCH (oms:Optical_Multiplex_Section)
        OPTIONAL MATCH (oms)-[r:Depends_on]->(dep)
        RETURN oms, collect(dep) as dependencies
        """

    oms_list = nc.query_to_list(nc.graphdb.manager, q)
    oms_list = _filter_operational_state(oms_list, request, select=lambda n: n.get('oms'))

    urls = get_node_urls(oms_list)

    table = Table("Optical Multiplex Section", "Description", "Depends on")
    table.rows = [_oms_table(item['oms'], item['dependencies']) for item in oms_list]
    _set_filters_operational_state(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Optical Multiplex Sections', 'urls': urls})


def _optical_nodes_table(node):
    row = TableRow(node, node.get('type'), node.get('link'), node.get('ots'))
    _set_operational_state(row, node)
    return row


@login_required
def list_optical_nodes(request):
    q = """
        MATCH (node:Optical_Node)
        RETURN node
        ORDER BY node.name
        """

    optical_node_list = nc.query_to_list(nc.graphdb.manager, q)
    optical_node_list = _filter_operational_state(optical_node_list, request, select=lambda n: n.get('node'))
    urls = get_node_urls(optical_node_list)

    table = Table('Name', 'Type', 'Link', 'OTS')
    table.rows = [_optical_nodes_table(item['node']) for item in optical_node_list]
    _set_filters_operational_state(table, request)
    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Optical Nodes', 'urls': urls})


def _optical_path_table(path):
    row = TableRow(
        path,
        path.get('framing'),
        path.get('capacity'),
        path.get('wavelength'),
        path.get('description'),
        ", ".join(path.get('enrs', [])))
    _set_operational_state(row, path)
    return row


@login_required
def list_optical_paths(request):
    q = """
        MATCH (path:Optical_Path)
        RETURN path
        ORDER BY path.name
        """

    optical_path_list = nc.query_to_list(nc.graphdb.manager, q)
    optical_path_list = _filter_operational_state(optical_path_list, request, select=lambda n: n.get('path'))
    urls = get_node_urls(optical_path_list)

    table = Table('Optical Path', 'Framing', 'Capacity', 'Wavelength', 'Description', 'ENRs')
    table.rows = [_optical_path_table(item['path']) for item in optical_path_list]
    _set_filters_operational_state(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Optical Paths', 'urls': urls})


def _peering_partner_table(peer, peering_groups):
    row = TableRow(peer, peer.get('as_number'), peering_groups)
    _set_expired(row, peer)
    return row


@login_required
def list_peering_partners(request):
    q = """
        MATCH (peer:Peering_Partner)
        OPTIONAL MATCH (peer)-[:Uses]->(peering_group)
        WITH distinct peer, peering_group
        RETURN peer, collect(peering_group) as peering_groups
        ORDER BY peer.name
        """

    partner_list = nc.query_to_list(nc.graphdb.manager, q)
    partner_list = _filter_expired(partner_list, request, select=lambda n: n.get('peer'))
    urls = get_node_urls(partner_list)

    table = Table('Peering Partner', 'AS Number', 'Peering Groups')
    table.rows = [_peering_partner_table(item['peer'], item['peering_groups']) for item in partner_list]
    _set_filters_expired(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Peering Partners', 'urls': urls})


@login_required
def list_racks(request):
    q = """
        MATCH (rack:Rack)
        OPTIONAL MATCH (rack)<-[:Has]-(loc)
        OPTIONAL MATCH p=(loc)<-[:Has*0..20]-()
        WITH COLLECT(nodes(p)) as paths, MAX(length(nodes(p))) AS maxLength, rack AS rack
        WITH FILTER(path IN paths WHERE length(path)=maxLength) AS longestPaths, rack AS rack
        UNWIND CASE WHEN longestPaths = [] THEN [null] ELSE longestPaths END as location_path
        RETURN rack, reverse(location_path) as location_path
        ORDER BY rack.name
        """

    rack_list = nc.query_to_list(nc.graphdb.manager, q)
    urls = get_node_urls(rack_list)

    table = Table('Name', 'Location')
    table.no_badges = True

    for item in rack_list:
        rack = item.get('rack')
        location_path = item.get('location_path')
        table.rows.append(TableRow(rack, location_path))

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Racks', 'urls': urls})


@login_required
def list_rooms(request):
    q = """
        MATCH (room:Room)
        RETURN room
        ORDER BY room.name
        """

    room_list = nc.query_to_list(nc.graphdb.manager, q)
    urls = get_node_urls(room_list)

    table = Table('Name', 'Location')
    for item in room_list:
        room = item.get('room')
        nh = get_object_or_404(NodeHandle, pk=room.get('handle_id'))
        node = nh.get_node()
        location_path = node.get_location_path()
        table.rows.append(TableRow(item['room'], location_path.get('location_path')))

    table.no_badges = True

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Rooms', 'urls': urls})


def _router_table(router):
    row = TableRow(router, router.get('model'), router.get('version'), router.get('operational_state'))
    _set_expired(row, router)
    return row


@login_required
def list_routers(request):
    q = """
        MATCH (router:Router)
        RETURN router
        ORDER BY router.name
        """

    router_list = nc.query_to_list(nc.graphdb.manager, q)
    router_list = _filter_expired(router_list, request, select=lambda n: n.get('router'))
    urls = get_node_urls(router_list)

    table = Table('Router', 'Model', 'JUNOS version', 'Operational state')
    table.rows = [_router_table(item['router']) for item in router_list]
    _set_filters_expired(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Routers', 'urls': urls})


def _service_table(service, customers, end_users):
    row = TableRow(service,
                   service.get('service_class'),
                   service.get('service_type'),
                   service.get('description'),
                   customers,
                   end_users)
    _set_operational_state(row, service)
    return row


@login_required
def list_services(request, service_class=None):
    where_statement = ''
    name = 'Services'
    if service_class:
        where_statement = 'WHERE service.service_class = "%s"' % service_class
        name = '{} Services'.format(service_class)
    q = """
        MATCH (service:Service)
        %s
        OPTIONAL MATCH (service)<-[:Uses]-(customer:Customer)
        WITH service, COLLECT(customer) as customers
        OPTIONAL MATCH (service)<-[:Uses]-(end_user:End_User)
        RETURN service, customers, COLLECT(end_user) as end_users
        ORDER BY service.name
        """ % where_statement

    service_list = nc.query_to_list(nc.graphdb.manager, q)
    service_list = _filter_operational_state(service_list, request, select=lambda n: n.get('service'))
    urls = get_node_urls(service_list)

    table = Table('Service',
                  'Service Class',
                  'Service Type',
                  'Description',
                  'Customers',
                  'End Users')
    table.rows = [_service_table(item['service'], item['customers'], item['end_users']) for item in service_list]

    _set_filters_operational_state(table, request)

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': name, 'urls': urls})


def _site_table(site):
    country_link = {
        'url': u'/findin/site/country_code/{}/'.format(site.get('country_code')),
        'name': u'{}'.format(site.get('country', '')),
    }
    area = site.get('area') or site.get('postarea')
    row = TableRow(country_link, site, area)
    return row


@login_required
def list_sites(request):
    q = """
        MATCH (site:Site)
        RETURN site
        ORDER BY site.country_code, site.name
        """

    site_list = nc.query_to_list(nc.graphdb.manager, q)
    urls = get_node_urls(site_list)

    table = Table('Country', 'Site name', 'Area')
    table.rows = [_site_table(item['site']) for item in site_list]
    table.no_badges = True

    return render(request, 'noclook/list/list_generic.html',
                  {'table': table, 'name': 'Sites', 'urls': urls})
