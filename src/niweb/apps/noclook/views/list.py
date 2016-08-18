# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.contrib.auth.decorators import login_required
from django.shortcuts import  get_object_or_404, render
from django.template import RequestContext

from apps.noclook.models import NodeType, NodeHandle
from apps.noclook.views.helpers import Table, TableRow
from apps.noclook.helpers import get_node_urls, find_recursive, neo4j_data_age
import norduniclient as nc

OPERATIONAL_BADGES = [
        ('badge-info', 'Testing'),
        ('badge-warning', 'Reserved'),
        ('badge-important', 'Decommissioned')]

def is_expired(node):
    last_seen, expired = neo4j_data_age(node)
    return expired
def _set_expired(row, node):
    if is_expired(node):
        row.classes = 'expired'
def _set_operational_state(row, node):
    if node.get('operational_state'):
        row.classes = node.get('operational_state').lower()


def _type_table(wrapped_node):
    node = wrapped_node.get('node')
    row = TableRow(node)
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
    node_list = nc.query_to_list(nc.neo4jdb, q)
    #Since all is the same type... we could use a defaultdict with type/id return
    urls = get_node_urls(node_list)
    table = Table('Name')
    table.rows = [ _type_table(node) for node in node_list]

    return render(request, 'noclook/list/list_generic.html',
            {'table': table, 'name': '{}s'.format(node_type), 'urls': urls})


def _cable_table(wrapped_cable):
    cable = wrapped_cable.get('cable')
    row = TableRow(cable, cable.get('cable_type'))
    _set_expired(row,cable)
    return row

@login_required
def list_cables(request):
    q = """
        MATCH (cable:Cable)
        RETURN cable
        ORDER BY cable.name
        """
    cable_list = nc.query_to_list(nc.neo4jdb, q)
    urls = get_node_urls(cable_list)

    table = Table('Name', 'Cable type')
    table.rows = [ _cable_table(cable) for cable in cable_list]

    return render(request, 'noclook/list/list_generic.html',
            {'table': table, 'name': 'Cables', 'urls': urls})

def _host_table(host, users):
    ip_addresses = host.get('ip_addresses', ['No address'])
    os = host.get('os')
    os_version = host.get('os_version')
    row = TableRow(host, ip_addresses, os, os_version, users)
    _set_expired(row, host)
    return row

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

    table = Table('Host', 'Address', 'OS', 'OS version', 'User')
    table.rows = [ _host_table(host, users) for host, users in host_list]

    return render(request, 'noclook/list/list_generic.html', {'table': table,'name': 'Hosts', 'urls': urls})

def _switch_table(switch, users):
    ip_addresses = switch.get('ip_addresses',['No address'])
    row =  TableRow(switch, ip_addresses, users)
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
    with nc.neo4jdb.read as r:
        switch_list = r.execute(q).fetchall()
    urls = get_node_urls(switch_list)

    table = Table('Switch', 'Address', 'User')
    table.rows = [ _switch_table(switch, users) for switch, users in switch_list]

    return render(request,'noclook/list/list_generic.html', 
                    {'name': 'Switches', 'table': table, 'urls': urls})

def _odf_table(item):
    location = item.get('location')
    odf = item.get('odf')
    site = item.get('site')
    # manipulate location name to include site name
    location_names = []
    if site and site.get('name'):
        location_names.append(site.get('name'))
    if location:
        if location.get('name'):
            location_names.append(location.get('name'))
        location['name'] = ' '.join(location_names)
    row = TableRow(location, odf)
    _set_expired(row, odf)
    return row

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

    table = Table("Location", "Name")
    table.rows = [ _odf_table(item) for item in odf_list]

    return render(request,'noclook/list/list_generic.html',
            {'table': table, 'name': 'ODFs', 'urls': urls})

def _optical_link_table(link, dependencies):
    for deps in dependencies:
        node = deps[0]
        if node and len(deps) > 1:
            name = [ n.get('name') for n in reversed(deps) if n]
            node['name'] = u' '.join(name)
    dependencies = [ deps[0] for deps in dependencies ]
    row = TableRow(link, link.get('link_type'), link.get('description'), dependencies)
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
    optical_link_list = nc.query_to_list(nc.neo4jdb, q)
    with nc.neo4jdb.read as r:
        optical_link_list = r.execute(q).fetchall()

    table = Table('Optical Link', 'Type', 'Description', 'Depends on')
    table.rows = [ _optical_link_table(link, dependencies) for link, dependencies in optical_link_list]
    table.badges = OPERATIONAL_BADGES

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
    with nc.neo4jdb.read as r:
        result = r.execute(q).fetchall()

    urls = get_node_urls(result)

    table = Table("Optical Multiplex Section", "Description", "Depends on")
    table.rows = [ _oms_table(oms, dependencies) for oms, dependencies in result]
    table.badges = OPERATIONAL_BADGES

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
    with nc.neo4jdb.read as r:
        optical_node_list = r.execute(q).fetchall()
    urls = get_node_urls(optical_node_list)

    table = Table('Name', 'Type', 'Link', 'OTS')
    table.rows = [ _optical_nodes_table(node[0]) for node in optical_node_list ]
    table.badges = OPERATIONAL_BADGES
    return render(request, 'noclook/list/list_generic.html',
            {'table': table, 'name': 'Optical Nodes', 'urls': urls})


def _optical_path_table(path):
    row = TableRow(
            path, 
            path.get('framing'), 
            path.get('capacity'), 
            path.get('description'),
            ", ".join(path.get('enrs',[])))
    _set_operational_state(row, path)
    return row

@login_required
def list_optical_paths(request):
    q = """
        MATCH (path:Optical_Path)
        RETURN path
        ORDER BY path.name
        """
    with nc.neo4jdb.read as r:
        optical_path_list = r.execute(q).fetchall()
    urls = get_node_urls(optical_path_list)
    print optical_path_list

    table = Table('Optical Path', 'Framing', 'Capacity', 'Description', 'ENRs')
    table.rows = [ _optical_path_table(path[0]) for path in optical_path_list ]
    table.badges = OPERATIONAL_BADGES

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
        OPTIONAL MATCH peer-[:Uses]->peering_group
        WITH distinct peer, peering_group
        RETURN peer, collect(peering_group) as peering_groups
        ORDER BY peer.name
        """
    with nc.neo4jdb.read as r:
        partner_list = r.execute(q).fetchall()
    urls = get_node_urls(partner_list)

    table = Table('Peering Partner', 'AS Number', 'Peering Groups')
    table.rows = [ _peering_partner_table(peer, groups) for peer, groups in partner_list]

    return render(request,'noclook/list/list_generic.html', 
            {'table': table, 'name': 'Peering Partners', 'urls': urls})


@login_required
def list_racks(request):
    q = """
        MATCH (rack:Rack)
        OPTIONAL MATCH rack<-[:Has]-site
        RETURN rack, site
        ORDER BY site.name, rack.name
        """
    with nc.neo4jdb.read as r:
       rack_list = r.execute(q).fetchall()
    urls = get_node_urls(rack_list)

    table = Table('Site', 'Name')
    table.rows = [ TableRow(site, rack) for rack, site in rack_list ]
    table.no_badges = True

    return render(request, 'noclook/list/list_generic.html',
            {'table': table, 'name': 'Racks',  'urls':urls})


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
    with nc.neo4jdb.read as r:
       router_list = r.execute(q).fetchall()
    urls = get_node_urls(router_list)

    table = Table('Router', 'Model', 'JUNOS version', 'Operational state')
    table.rows = [ _router_table(router[0]) for router in router_list ]

    return render(request, 'noclook/list/list_generic.html',
            {'table': table, 'name': 'Routers', 'urls':urls})

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
    with nc.neo4jdb.read as r:
       service_list = r.execute(q).fetchall()
    urls = get_node_urls(service_list)

    table = Table('Service',
                'Service Class', 
                'Service Type', 
                'Description', 
                'Customers', 
                'End Users')
    table.rows = [ _service_table(service, customers, end_users) for service, customers, end_users in service_list ]
    table.badges=OPERATIONAL_BADGES

    return render(request, 'noclook/list/list_generic.html',
                              {'table': table, 'name': name, 'urls': urls})

def _site_table(site):
    country_link = {
            'url': u'/findin/site/country_code/{}/'.format(site.get('country_code')),
            'name': u'{}'.format(site.get('country', ''))
            }
    area = site.get('area') or ite.get('postarea')
    row = TableRow(country_link, site, area)
    return row

@login_required
def list_sites(request):
    q = """
        MATCH (site:Site)
        RETURN site
        ORDER BY site.country_code, site.name
        """
    with nc.neo4jdb.read as r:
       site_list = r.execute(q).fetchall()
    urls = get_node_urls(site_list)

    table = Table('Country', 'Site name', 'Area')
    table.rows = [ _site_table(site[0]) for site in site_list ]
    table.no_badges=True


    return render(request, 'noclook/list/list_generic.html',
            {'table': table, 'name': 'Sites', 'urls': urls})








