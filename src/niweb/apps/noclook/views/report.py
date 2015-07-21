# -*- coding: utf-8 -*-
"""
Created on 2012-06-11 5:48 PM

@author: lundberg
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, render
from django.template import RequestContext
from django.http import Http404, HttpResponse
from django.template.defaultfilters import yesno, date
from django.views.decorators.cache import cache_page
from django.conf import settings as django_settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import tempfile
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
from decimal import Decimal, ROUND_DOWN

from apps.noclook.forms import get_node_type_tuples, SearchIdForm
from apps.noclook.forms.reports import HostReportForm
from apps.noclook.models import NordunetUniqueId
from apps.noclook.templatetags.noclook_tags import timestamp_to_td
from apps.noclook import helpers
import norduniclient as nc


@login_required
def host_reports(request):
    return render_to_response('noclook/reports/host_reports.html', {},
                              context_instance=RequestContext(request))


@login_required
def host_users(request, host_user_name=None):
    hosts = []
    users = dict([(name, uid) for uid, name in get_node_type_tuples('Host User') if name])
    host_user_id = users.get(host_user_name, None)
    form = HostReportForm(request.GET or {'cut_off': '1'})

    if host_user_id:
        q = '''
            MATCH (host_user:Host_User {handle_id: {handle_id}})-[:Uses|Owns]->(host:Host)
            {where}
            RETURN host_user, collect(DISTINCT {data: host, type: filter(x in labels(host) where not x in ['Node', 'Host'])}) as hosts
            '''.replace("{where}", form.to_where())
        hosts = nc.query_to_list(nc.neo4jdb, q, handle_id=host_user_id)
    elif host_user_name == 'Missing':
        q = '''
            MATCH (host:Host)
            {where}
            RETURN collect(DISTINCT {data: host, type: filter(x in labels(host) where not x in ['Node', 'Host'])}) as hosts
          '''.replace("{where}", form.to_where(additional="NOT (host)<-[:Uses|Owns]-()"))
        hosts = nc.query_to_list(nc.neo4jdb, q)
    elif host_user_name == 'All' or host_user_name == None:
        q = '''
            MATCH (host_user:Host_User)-[:Uses|Owns]->(host:Host) 
            {where}
            RETURN host_user, collect(DISTINCT {data: host, type: filter(x in labels(host) where not x in ['Node', 'Host'])}) as hosts
            '''.replace("{where}", form.to_where())
        hosts = nc.query_to_list(nc.neo4jdb, q)
    num_of_hosts = 0
    for item in hosts:
        num_of_hosts += len(item['hosts'])

    urls = helpers.get_node_urls(hosts)
    return render_to_response('noclook/reports/host_users.html',
                              {'host_user_name': host_user_name, 'host_users': users, 'hosts': hosts,
                               'num_of_hosts': num_of_hosts, 'urls': urls, 'form': form},
                              context_instance=RequestContext(request))


@login_required
def host_security_class(request, status=None, form=None):
    hosts = []
    where_statement = ''
    if status == 'classified':
        where_statement = 'and (has(host.security_class) or has(host.security_comment))'
    elif status == 'not-classified':
        where_statement = 'and (not(has(host.security_class)) and not(has(host.security_comment)))'
    q = '''
            MATCH (host:Host)
            WHERE not(host.operational_state = "Decommissioned") %s
            RETURN host
            ORDER BY host.noclook_last_seen DESC
            ''' % where_statement
    hosts = nc.query_to_list(nc.neo4jdb, q)
    urls = helpers.get_node_urls(hosts)
    return render_to_response('noclook/reports/host_security_class.html',
                              {'status': status, 'hosts': hosts, 'urls': urls},
                              context_instance=RequestContext(request))


@login_required
def host_services(request, status=None):
    hosts = []
    if status:
        if status == 'unauthorized-ports':
            q = """
                MATCH (host:Host)
                MATCH host<-[r:Depends_on]-()
                WHERE has(r.rogue_port)
                RETURN host, collect(r) as ports
                ORDER BY host.noclook_last_seen DESC
                """
            hosts = nc.query_to_list(nc.neo4jdb, q)
            return render_to_response('noclook/reports/host_unauthorized_ports.html', 
                    {'status': status, 'hosts': hosts},
                    context_instance=RequestContext(request))
        else:
            where_statement = ''
            if status == 'locked':
                where_statement = 'and (has(host.services_locked) and host.services_locked)'
            elif status == 'not-locked':
                where_statement = 'and (not(has(host.services_locked)) or not host.services_locked)'
            q = """
                MATCH (host:Host)
                WHERE not(host.operational_state = "Decommissioned") %s
                RETURN host
                ORDER BY host.noclook_last_seen DESC
                """ % where_statement
        hosts = nc.query_to_list(nc.neo4jdb, q)
    return render_to_response('noclook/reports/host_services.html',
                              {'status': status, 'hosts': hosts},
                              context_instance=RequestContext(request))



def monthly_netapp_usage():
    """
    :return: Http200

    This should be run the 1st of every month.
    """

    return HttpResponse('Monthly NetApp usage saved.')


@login_required
def unique_ids(request, organisation=None):
    if not organisation:
        return render_to_response('noclook/reports/unique_ids/choose_organization.html', {}, context_instance=RequestContext(request))
    if organisation == 'NORDUnet':
        id_list = get_id_list(request.GET or None)
        id_list = helpers.paginate(id_list, request.GET.get('page'))
    else:
        raise Http404
    search_form = SearchIdForm(request.GET or None)
    return render_to_response('noclook/reports/unique_ids/list.html',
        {'id_list': id_list, 'organisation': organisation, 'search_form': search_form},
        context_instance=RequestContext(request))

@login_required
def download_unique_ids(request, organisation=None, file_format=None):
    header = ["ID", "Reserved", "Reserve message", "Site", "Reserver", "Created"]

    if organisation == 'NORDUnet':
        id_list = get_id_list(request.GET or None)
        get_site = lambda uid : uid.site.node_name if uid.site else ""
        create_dict = lambda uid : {'ID': uid.unique_id, 'Reserve message': uid.reserve_message, 'Reserved': uid.reserved, 'Site': get_site(uid), 'Reserver': str(uid.reserver), 'Created': uid.created}
        table = [ create_dict(uid)  for uid in id_list]
        # using values is faster, a lot, but no nice header :( and no username
        #table = id_list.values()
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
        #do stuff
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
