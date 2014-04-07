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
from django.views.decorators.cache import cache_page
from django.conf import settings as django_settings
from django.contrib.auth.models import User

import tempfile
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
from decimal import Decimal, ROUND_DOWN

from niweb.apps.noclook.forms import get_node_type_tuples
from niweb.apps.noclook.models import NordunetUniqueId
from niweb.apps.noclook.templatetags.noclook_tags import timestamp_to_td
import niweb.apps.noclook.helpers as h
import norduni_client as nc


@login_required
def host_reports(request):
    return render_to_response('noclook/reports/host_reports.html', {},
                              context_instance=RequestContext(request))


@cache_page(60 * 5)
@login_required
def host_users(request, host_user_name=None):
    users = dict([(name, uid) for uid, name in get_node_type_tuples('Host User') if name])
    host_user_id = users.get(host_user_name, None)
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
                              {'host_user_name': host_user_name, 'host_users': users, 'hosts': hosts},
                              context_instance=RequestContext(request))


@cache_page(60 * 5)
@login_required
def host_security_class(request, status=None, form=None):
    num_of_hosts = 0
    hosts = []
    where_statement = ''
    if status == 'classified':
        where_statement = 'and (has(node.security_class) or has(node.security_comment))'
    elif status == 'not-classified':
        where_statement = 'and (not(has(node.security_class)) and not(has(node.security_comment)))'
    if status:
        num_of_hosts_q = '''
            START node=node:node_types(node_type = "Host")
            WHERE not(node.operational_state! = "Decommissioned") %s
            RETURN COUNT(node) as num_of_hosts
            ''' % where_statement
        hosts_q = '''
            START node=node:node_types(node_type = "Host")
            WHERE not(node.operational_state! = "Decommissioned") %s
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


@cache_page(60 * 5)
@login_required
def host_services(request, status=None):
    hosts = []
    num_hosts = 0
    if status:
        if status == 'unauthorized-ports':
            q = """
                START node=node:node_types(node_type="Host")
                MATCH node<-[r:Depends_on]-()
                WHERE has(r.rogue_port)
                RETURN node, collect(r) as ports
                """
            hosts = nc.neo4jdb.query(q)
        else:
            where_statement = ''
            if status == 'locked':
                where_statement = 'and has(node.services_locked)'
            elif status == 'not-locked':
                where_statement = 'and not(has(node.services_locked))'
            q = """
                START node=node:node_types(node_type="Host")
                WHERE not(node.operational_state! = "Decommissioned") %s
                RETURN collect(node) as nodes, count(*) as num_hosts
                """ % where_statement
            for hit in nc.neo4jdb.query(q):
                hosts = hit['nodes']
                num_hosts = hit['num_hosts']
    return render_to_response('noclook/reports/host_services.html',
                              {'status': status, 'hosts': hosts, 'num_hosts': num_hosts},
                              context_instance=RequestContext(request))


def send_report(request, report, **kwargs):
    if request.META.get('HTTP_X_REPORT_KEY', None) == getattr(django_settings, 'REPORT_KEY'):
        if report == 'host-contract':
            contract_number = kwargs.get('contract_number', None)
            if contract_number:
                return mail_host_contract_report(contract_number)
        elif report == 'netapp-storage':
            period = kwargs.get('period', None)
            if period == 'monthly':
                return monthly_netapp_usage()
            elif period == 'quarterly':
                return quarterly_netapp_usage()
    return HttpResponse(content=u'Not authorized.', status=401)


def mail_host_contract_report(contract_number):
    """
    :param contract_number: String
    :return: HttpResponse(status=200)

    Sends mail to addresses specified in settings.REPORTS_TO with report attached.
    """
    utcnow = datetime.utcnow()
    last_month = utcnow - relativedelta(months=1)
    subject = 'NOCLook host report for %s' % contract_number
    to = getattr(django_settings, 'REPORTS_TO', [])
    cc = getattr(django_settings, 'REPORTS_CC', None)
    bcc = getattr(django_settings, 'REPORTS_BCC', None)
    extra_report = getattr(django_settings, 'EXTRA_REPORT_TO', {})
    extended_to = to + extra_report.get(contract_number, [])  # Avoid changing REPORTS_TO :)
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
        msg = h.create_email(subject, body, extended_to, cc, bcc, temp.read(), filename, 'application/excel')
        msg.send()
    return HttpResponse('Report for %s sent.' % contract_number)


def monthly_netapp_usage():
    """
    :return: Http200

    This should be run the 1st of every month.
    """
    user = User.objects.get(username='noclook')
    utcnow = datetime.utcnow()
    last_month = utcnow - relativedelta(months=1)
    services = getattr(django_settings, 'NETAPP_REPORT_SETTINGS', [])
    for service in services:
        service_node = nc.get_unique_node_by_name(nc.neo4jdb, service['service_id'], 'Service')
        monthly_dict = json.loads(service_node.get_property('netapp_storage_monthly', '{}'))
        monthly_dict.setdefault(str(last_month.year), {})[str(last_month.month)] = \
            service_node.get_property('netapp_storage_sum', 0.0)
        property_dict = {'netapp_storage_monthly': json.dumps(monthly_dict)}
        h.dict_update_node(user, service_node, property_dict, property_dict.keys())
    return HttpResponse('Monthly NetApp usage saved.')


def quarterly_netapp_usage():
    to = getattr(django_settings, 'REPORTS_TO', [])
    cc = getattr(django_settings, 'REPORTS_CC', None)
    bcc = getattr(django_settings, 'REPORTS_BCC', None)
    extra_report = getattr(django_settings, 'EXTRA_REPORT_TO', {})
    free_gb = Decimal('1000.00')
    price_per_gb = Decimal('0.40')
    quarter_month_map = {
        1: ['01', '02', '03'],
        2: ['04', '05', '06'],
        3: ['07', '08', '09'],
        4: ['10', '11', '12']
    }
    utcnow = datetime.utcnow()
    last_month = utcnow - relativedelta(months=1)
    year = str(last_month.year)
    last_quarter = (last_month.month-1)//3 + 1
    services = getattr(django_settings, 'NETAPP_REPORT_SETTINGS', [])
    for service in services:
        report_data = []
        service_node = nc.get_unique_node_by_name(nc.neo4jdb, service['service_id'], 'Service')
        try:
            customers = ', '.join([hit['customer'].get_property('name', '') for hit in h.get_customer(service_node)])
        except Exception:  # Neo4j embedded jpype exception
            customers = 'Missing customer name'
        data_dict = json.loads(service_node.get_property('netapp_storage_monthly', '{}')).get(year, None)
        if data_dict:
            for month in quarter_month_map[last_quarter]:
                key = '%s-%s' % (year, month)
                report_data.append({key: data_dict.get(month.lstrip('0'), 0.0)})
            # Create and send the mail
            subject = 'Storage cost for %s Q%d %s' % (service['contract_reference'], last_quarter, year)
            heading = 'Adobe connect storage volume billing Q%d, %s, for %s.' % (last_quarter, year, customers)
            body = '''
        This is an auto generated report from NOCLook for service ID %s.

        %s

        This report was generated on %s UTC.
            ''' % (service['service_id'], heading, utcnow.strftime('%Y-%m-%d %H:%M'))
            extended_to = to + extra_report.get(service['service_id'], [])  # Avoid changing REPORTS_TO :)
            filename = 'Storage cost for %s Q%d %s.xls' % (service['contract_reference'], last_quarter, year)
            wb = h.dicts_to_xls({}, [], '%s Q%d %s' % (service['service_id'], last_quarter, year))
            # Calculate and write pricing info
            ws = wb.get_sheet(0)
            ws.write(1, 1, heading)
            ws.write(2, 1, 'Reference: %s' % service['contract_reference'])
            ws.write(4, 1, 'Month')
            ws.write(4, 2, 'Storage (GB)')
            ws.write(4, 3, 'Service inc.')
            ws.write(4, 4, 'Billable storage')
            ws.write(4, 5, u'Price per GB (€)')
            ws.write(4, 6, u'Monthly cost (€)')
            total_cost = Decimal(0)
            for i in range(0, len(report_data)):
                row = 5 + i
                storage_month = Decimal(report_data[i].values()[0])
                billable = Decimal(max(storage_month-free_gb, 0))
                cost_month = billable * price_per_gb
                total_cost += cost_month
                ws.write(row, 1, report_data[i].keys()[0])
                ws.write(row, 2, storage_month.quantize(Decimal('.01'), rounding=ROUND_DOWN))
                ws.write(row, 3, -free_gb.quantize(Decimal('.01'), rounding=ROUND_DOWN))
                ws.write(row, 4, billable.quantize(Decimal('.01'), rounding=ROUND_DOWN))
                ws.write(row, 5, price_per_gb.quantize(Decimal('.01'), rounding=ROUND_DOWN))
                ws.write(row, 6, cost_month.quantize(Decimal('.01'), rounding=ROUND_DOWN))
            ws.write(9, 1, 'Quarterly storage cost')
            ws.write(9, 6, total_cost.quantize(Decimal('.01'), rounding=ROUND_DOWN))
            with tempfile.TemporaryFile() as temp:
                wb.save(temp)
                temp.seek(0)
                msg = h.create_email(subject, body, extended_to, cc, bcc, temp.read(), filename, 'application/excel')
                msg.send()
    return HttpResponse('Quarterly NetApp storage reports sent!')


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