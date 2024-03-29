# -*- coding: utf-8 -*-
"""
Created on 2012-06-11 5:48 PM

@author: lundberg
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import Http404

from apps.noclook.forms import get_node_type_tuples, SearchIdForm
from apps.noclook.forms.reports import HostReportForm
from apps.noclook.models import NordunetUniqueId, NodeHandle
from apps.noclook import helpers
import norduniclient as nc


@login_required
def host_reports(request):
    return render(request, 'noclook/reports/host_reports.html', {})


@login_required
def host_users(request, host_user_name=None):
    hosts = []
    users = dict([(name, uid) for uid, name in get_node_type_tuples('Host User') if name])
    host_user_id = users.get(host_user_name, None)
    form = HostReportForm(request.GET or {'cut_off': '1'})

    if host_user_id:
        q = '''
            MATCH (host_user:Host_User {handle_id: $handle_id})-[:Uses|Owns]->(host:Host)
            {where}
            RETURN host_user, collect(DISTINCT {data: host, type: [x in labels(host) where not x in ['Node', 'Host']]}) as hosts
            '''.replace("{where}", form.to_where())
        hosts = nc.query_to_list(nc.graphdb.manager, q, handle_id=host_user_id)
    elif host_user_name == 'Missing':
        q = '''
            MATCH (host:Host)
            {where}
            RETURN collect(DISTINCT {data: host, type: [x in labels(host) where not x in ['Node', 'Host']]}) as hosts
          '''.replace("{where}", form.to_where(additional="NOT (host)<-[:Uses|Owns]-()"))
        hosts = nc.query_to_list(nc.graphdb.manager, q)
    elif host_user_name == 'All' or host_user_name is None:
        q = '''
            MATCH (host_user:Host_User)-[:Uses|Owns]->(host:Host) 
            {where}
            RETURN host_user, collect(DISTINCT {data: host, type: [x in labels(host) where not x in ['Node', 'Host']]}) as hosts
            '''.replace("{where}", form.to_where())
        hosts = nc.query_to_list(nc.graphdb.manager, q)
    num_of_hosts = 0
    for item in hosts:
        num_of_hosts += len(item['hosts'])

    urls = helpers.get_node_urls(hosts)
    return render(request, 'noclook/reports/host_users.html',
                              {'host_user_name': host_user_name, 'host_users': users, 'hosts': hosts,
                               'num_of_hosts': num_of_hosts, 'urls': urls, 'form': form})


@login_required
def host_security_class(request, status=None, form=None):
    where_statement = ''
    if status == 'classified':
        where_statement = 'and (exists(host.security_class) or exists(host.security_comment))'
    elif status == 'not-classified':
        where_statement = 'and (not(exists(host.security_class)) and not(exists(host.security_comment)))'
    q = '''
            MATCH (host:Host)
            WHERE not(host.operational_state = "Decommissioned") %s
            RETURN host
            ORDER BY host.noclook_last_seen DESC
            ''' % where_statement
    hosts = nc.query_to_list(nc.graphdb.manager, q)
    urls = helpers.get_node_urls(hosts)
    return render(request, 'noclook/reports/host_security_class.html',
                              {'status': status, 'hosts': hosts, 'urls': urls})


@login_required
def host_services(request, status=None):
    hosts = []
    if status:
        if status == 'unauthorized-ports':
            q = """
                MATCH (host:Host)
                MATCH (host)<-[r:Depends_on]-()
                WHERE host.operational_state <> "Decommissioned" and exists(r.rogue_port)
                RETURN host, collect(r) as ports
                ORDER BY host.noclook_last_seen DESC
                """
            hosts = nc.query_to_list(nc.graphdb.manager, q)
            return render(request, 'noclook/reports/host_unauthorized_ports.html',
                                      {'status': status, 'hosts': hosts})
        elif status == 'public':
            q = """
                MATCH (host:Host)
                MATCH (host)<-[r:Depends_on]-()
                WHERE host.operational_state <> "Decommissioned" and r.public
                RETURN host, collect({data: r, id: id(r)}) as ports
                ORDER BY host.noclook_last_seen DESC
                """
            hosts = nc.query_to_list(nc.graphdb.manager, q)
            return render(request, 'noclook/reports/host_public_ports.html',
                                      {'status': status, 'hosts': hosts})
        else:
            if status == 'locked':
                where_statement = 'and (exists(host.services_locked) and host.services_locked)'
            elif status == 'not-locked':
                where_statement = 'and (not(exists(host.services_locked)) or not host.services_locked)'
            else:
                raise Http404()
            q = """
                MATCH (host:Host)
                WHERE host.operational_state <> "Decommissioned" %s
                RETURN host
                ORDER BY host.noclook_last_seen DESC
                """ % where_statement
        hosts = nc.query_to_list(nc.graphdb.manager, q)
    return render(request, 'noclook/reports/host_services.html',
                              {'status': status, 'hosts': hosts})


@login_required
def unique_ids(request):
    id_list = get_id_list(request.GET or None)
    id_list = helpers.paginate(id_list, request.GET.get('page'))
    search_form = SearchIdForm(request.GET or None)
    return render(request, 'noclook/reports/unique_ids/list.html',
        {'id_list': id_list, 'search_form': search_form})


@login_required
def download_unique_ids(request, file_format=None):
    header = ["ID", "Reserved", "Reserve message", "Site", "Reserver", "Created"]
    table = None
    id_list = get_id_list(request.GET or None)

    def get_site(uid):
        return uid.site.node_name if uid.site else ""

    def create_dict(uid):
        return {
            'ID': uid.unique_id,
            'Reserve message': uid.reserve_message,
            'Reserved': uid.reserved,
            'Site': get_site(uid),
            'Reserver': str(uid.reserver),
            'Created': uid.created
        }
    table = [create_dict(uid) for uid in id_list]
    # using values is faster, a lot, but no nice header :( and no username
    # table = id_list.values()
    if table and file_format == 'xls':
        return helpers.dicts_to_xls_response(table, header)
    elif table and file_format == 'csv':
        return helpers.dicts_to_csv_response(table, header)
    else:
        raise Http404


def get_id_list(data=None):
    id_list = NordunetUniqueId.objects.all().prefetch_related('reserver').prefetch_related('site')
    form = SearchIdForm(data)
    if form.is_valid():
        # do stuff
        data = form.cleaned_data
        if data['reserved']:
            id_list = id_list.filter(reserved=data['reserved'])
        if data['reserve_message']:
            id_list = id_list.filter(reserve_message__icontains=data['reserve_message'])
        if data['site']:
            id_list = id_list.filter(site=data['site'])
        if data['id_type']:
            id_list = id_list.filter(unique_id__startswith=data['id_type'])
    return id_list.order_by('created').reverse()


@login_required
def download_rack_cables(request, handle_id, file_format=None):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    node = nh.get_node()
    location = '_'.join([loc['name'] for loc in node.get_location_path()['location_path']])
    header = [
        'EquipmentA',
        'PortA',
        'Cable',
        'CableType',
        'EquipmentB',
        'PortB',
    ]
    q = """
    MATCH (r:Rack {handle_id: $handle_id})<-[:Located_in]-(n:Node)-[:Has]->(p:Port)<-[:Connected_to]-(c:Cable)-[:Connected_to]->(p2:Port)<-[:Has]-(n2:Node)
    WHERE n <> n2 and p <> p2
    RETURN n.name AS EquipmentA, p.name AS PortA, c.name AS Cable, c.cable_type AS CableType, n2.name AS EquipmentB, p2.name AS PortB
    """

    cables = nc.query_to_list(nc.graphdb.manager, q, handle_id=nh.handle_id)

    file_name = 'rack-cables_{}_{}_{}.{}'.format(location, nh.node_name, nh.handle_id, file_format)
    if cables and file_format == 'xls':
        sheet_name = '{} - {}'.format(location, nh.node_name)
        return helpers.dicts_to_xls_response(cables, header, file_name, sheet_name=sheet_name)
    elif cables and file_format == 'csv':
        return helpers.dicts_to_csv_response(cables, header, file_name)
    else:
        raise Http404
