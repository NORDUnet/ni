# -*- coding: utf-8 -*-
"""
Created on 2012-06-11 5:48 PM

@author: lundberg
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import Http404, HttpResponse
from django.template.defaultfilters import yesno, date
import tempfile
from datetime import datetime, timedelta
from django.conf import settings as django_settings

from niweb.apps.noclook.forms import get_node_type_tuples
from niweb.apps.noclook.models import NordunetUniqueId
from niweb.apps.noclook.templatetags.noclook_tags import timestamp_to_td
import niweb.apps.noclook.helpers as h
import norduni_client as nc


@login_required
def host_reports(request):
    return render_to_response('noclook/reports/host_reports.html', {},
                              context_instance=RequestContext(request))


@login_required
def host_users(request, host_user_name=None):
    host_users = get_node_type_tuples('Host User')
    host_users = dict([[name,id] for id,name in host_users if name])
    host_user_id = host_users.get(host_user_name, None)
    hosts = []
    if host_user_id:
        hosts_q = '''
            START host_user=node({id})
            MATCH host_user-[r:Uses|Owns]->host<-[:Contains]-meta
            RETURN host_user, host, meta.name as host_type
            ORDER BY host_user.name, host.name
            '''
    elif host_user_name == 'Missing':
        hosts_q = '''
                START host=node:node_types(node_type = "Host")
                MATCH meta-[:Contains]->host<-[r?:Uses|Owns]-()
                WHERE r is null
                RETURN host, meta.name as host_type
                ORDER BY host.name
                '''
    else:
        hosts_q = '''
                START host_user=node:node_types(node_type = "Host User")
                MATCH host_user-[r:Uses|Owns]->host<-[:Contains]-meta
                RETURN host_user, host, meta.name as host_type
                ORDER BY host_user.name, host.name
                '''
    if host_user_id:
        hosts = [hit for hit in nc.neo4jdb.query(hosts_q, id=host_user_id)]
    elif host_user_name:
        hosts = [hit for hit in nc.neo4jdb.query(hosts_q)]
    return render_to_response('noclook/reports/host_users.html',
                              {'host_user_name': host_user_name, 'host_users': host_users, 'hosts': hosts},
                              context_instance=RequestContext(request))


@login_required
def host_security_class(request, status=None, form=None):
    num_of_hosts = 0
    hosts = []
    where_statement = ''
    if status == 'classified':
        where_statement = 'WHERE has(node.security_class) or has(node.security_comment)'
    elif status == 'not-classified':
        where_statement = 'WHERE not(has(node.security_class)) and not(has(node.security_comment))'
    if status:
        num_of_hosts_q = '''
            START node=node:node_types(node_type = "Host")
            %s
            RETURN COUNT(node) as num_of_hosts
            ''' % where_statement
        hosts_q = '''
            START node=node:node_types(node_type = "Host")
            %s
            RETURN node, node.name as host_name,
            node.description? as description,
            node.security_class? as security_class,
            node.security_comment? as security_comment,
            node.noclook_last_seen as last_seen
            ''' % where_statement
        num_of_hosts_hits = nc.neo4jdb.query(num_of_hosts_q)
        num_of_hosts = [hit['num_of_hosts'] for hit in num_of_hosts_hits][0]
        hosts = nc.neo4jdb.query(hosts_q)
    return render_to_response('noclook/reports/host_security_class.html',
                              {'status': status, 'num_of_hosts': num_of_hosts, 'hosts': hosts},
                              context_instance=RequestContext(request))


def send_report(request, report, **kwargs):
    if request.META.get('HTTP_X_REPORT_KEY', None) == getattr(django_settings, 'REPORT_KEY'):
        if report == 'host-contract':
            contract_number = kwargs.get('contract_number', None)
            if contract_number:
                return mail_host_contract_report(contract_number)
    return HttpResponse(content=u'Not authorized.', status=401)


def mail_host_contract_report(contract_number):
    """
    :param contract_number: String
    :return: HttpResponse(status=200)

    Sends mail to addresses specified in settings.REPORTS_TO with report attached.
    """
    utcnow = datetime.utcnow()
    last_month = utcnow - timedelta(days=utcnow.day)
    subject = 'NOCLook host report for %s' % contract_number
    to = getattr(django_settings, 'REPORTS_TO', [])
    cc = getattr(django_settings, 'REPORTS_CC', None)
    bcc = getattr(django_settings, 'REPORTS_BCC', None)
    body = '''
    This is an auto generated report from NOCLook for contract number %s.

    This report was generated on %s UTC.
        ''' % (contract_number, utcnow.strftime('%Y-%m-%d %H:%M'))
    price_per_host = 120
    header = [
        'Host user',
        'Host',
        'Host type',
        'IP address(es)',
        'Contract number',
        'Description',
        'Responsible',
        'Backup',
        'Syslog',
        'Nagios',
        'Operational State',
        'Security Class',
        'Location',
        'Last seen',
        'Uptime (days)'
    ]
    result = []
    hosts_q = '''
        START host=node:node_types(node_type = "Host")
        MATCH host_user-[r:Uses|Owns]->host<-[:Contains]-meta
        WHERE host.contract_number! = {contract_number}
        RETURN host_user, host, meta.name as host_type
        ORDER BY host_user.name, host.name
        '''
    for hit in nc.neo4jdb.query(hosts_q, contract_number=contract_number):
        age = h.neo4j_report_age(hit['host'], 15, 30)
        operational_state = hit['host'].get_property('operational_state', 'Not set')
        host_type = hit['host_type']
        host_user = hit['host_user']['name']
        uptime = hit['host'].get_property('uptime', '')
        if uptime:
            uptime = timestamp_to_td(uptime).days
        if host_type == 'logical' and age != 'very_old' and operational_state != 'Decommissioned':
            values = [
                unicode(host_user),
                unicode(hit['host']['name']),
                unicode(host_type).capitalize(),
                u', '.join([address for address in hit['host']['ip_addresses']]),
                unicode(hit['host']['contract_number']),
                unicode(hit['host'].get_property('description', '')),
                unicode(hit['host'].get_property('responsible_group', '')),
                unicode(hit['host'].get_property('backup', 'Not set')),
                unicode(yesno(hit['host'].get_property('syslog', None), 'Yes,No,Not set')),
                unicode(yesno(hit['host'].get_property('nagios_checks', False), 'Yes,No,Not set')),
                unicode(operational_state),
                unicode(hit['host'].get_property('security_class', '')),
                unicode(''),
                unicode(date(h.isots_to_dt(hit['host']), "Y-m-d")),
                unicode(uptime),
            ]
            result.append(dict(zip(header, values)))
    num_hosts = len(result)
    filename = '%s hosts %s.xls' % (contract_number, last_month.strftime('%B %Y'))
    wb = h.dicts_to_xls(result, header, contract_number)
    # Calculate and write pricing info
    ws = wb.get_sheet(0)
    ws.write(num_hosts + 2, 1, 'Number of Virtual Servers')
    ws.write(num_hosts + 2, 4, '%d' % num_hosts)
    ws.write(num_hosts + 3, 1, 'Price')
    ws.write(num_hosts + 3, 4, '%d' % price_per_host)
    ws.write(num_hosts + 4, 1, 'Total Invoice amount ex. VAT')
    ws.write(num_hosts + 4, 4, '%d' % (num_hosts*price_per_host))
    with tempfile.TemporaryFile() as temp:
        wb.save(temp)
        temp.seek(0)
        msg = h.create_email(subject, body, to, cc, bcc, temp.read(), filename, 'application/excel')
        msg.send()
    return HttpResponse('Report for %s sent.' % contract_number)


@login_required
def unique_ids(request, organisation=None):
    if not organisation:
        return render_to_response('noclook/reports/unique_ids.html', {},
            context_instance=RequestContext(request))
    if organisation == 'NORDUnet':
        id_list = NordunetUniqueId.objects.all().order_by('unique_id')
    else:
        raise Http404
    return render_to_response('noclook/reports/unique_ids.html',
        {'id_list': id_list, 'organisation': organisation},
        context_instance=RequestContext(request))