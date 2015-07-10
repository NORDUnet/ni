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
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import tempfile
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
from decimal import Decimal, ROUND_DOWN

from apps.noclook.forms import get_node_type_tuples, SearchIdForm
from apps.noclook.models import NordunetUniqueId
from apps.noclook.templatetags.noclook_tags import timestamp_to_td
from apps.noclook import helpers
import norduniclient as nc


@login_required
def host_reports(request):
    return render_to_response('noclook/reports/host_reports.html', {},
                              context_instance=RequestContext(request))


@cache_page(60 * 5)
@login_required
def host_users(request, host_user_name=None):
    hosts = []
    users = dict([(name, uid) for uid, name in get_node_type_tuples('Host User') if name])
    host_user_id = users.get(host_user_name, None)
    if host_user_id:
        host_user = nc.get_node_model(nc.neo4jdb, host_user_id).data
        q = '''
            MATCH (host_user:Host_User {handle_id: {handle_id}})-[:Uses|Owns]->(host:Host)
            RETURN collect(DISTINCT host.handle_id) as ids
            '''
        hosts = [{
                'host_user': host_user,
                'ids': nc.query_to_dict(nc.neo4jdb, q, handle_id=host_user_id)['ids']
            }]
    elif host_user_name == 'Missing':
        q = '''
            MATCH (host:Host)
            WHERE NOT (host)<-[:Uses|Owns]-()
            RETURN collect(host.handle_id) as ids
                '''
        hosts = nc.query_to_list(nc.neo4jdb, q)
    elif host_user_name == 'All':
        q = '''
            MATCH (host_user:Host_User)-[:Uses|Owns]->(host:Host)
            RETURN host_user, collect(DISTINCT host.handle_id) as ids
                '''
        hosts = nc.query_to_list(nc.neo4jdb, q)
    num_of_hosts = 0
    for item in hosts:
        num_of_hosts += len(item['ids'])
    return render_to_response('noclook/reports/host_users.html',
                              {'host_user_name': host_user_name, 'host_users': users, 'hosts': hosts,
                               'num_of_hosts': num_of_hosts},
                              context_instance=RequestContext(request))


@cache_page(60 * 5)
@login_required
def host_security_class(request, status=None, form=None):
    hosts = []
    where_statement = ''
    if status == 'classified':
        where_statement = 'and (has(host.security_class) or has(host.security_comment))'
    elif status == 'not-classified':
        where_statement = 'and (not(has(host.security_class)) and not(has(host.security_comment)))'
    if status:
        q = '''
            MATCH (host:Host)
            WHERE not(host.operational_state = "Decommissioned") %s
            RETURN host
            ''' % where_statement
        hosts = nc.query_to_list(nc.neo4jdb, q)
    return render_to_response('noclook/reports/host_security_class.html',
                              {'status': status, 'hosts': hosts},
                              context_instance=RequestContext(request))


@cache_page(60 * 5)
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
                """
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
                """ % where_statement
        hosts = nc.query_to_list(nc.neo4jdb, q)
    return render_to_response('noclook/reports/host_services.html',
                              {'status': status, 'hosts': hosts},
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
    q = '''
        MATCH (host_user:Host_User)-[r:Uses|Owns]->(host:Host)
        WHERE host.contract_number = {contract_number}
        RETURN host_user.name as host_user_name, host.name, host.handle_id as host_handle_id
        ORDER BY host_user.name, host.name
        '''
    for item in nc.query_to_list(nc.neo4jdb, q, contract_number=contract_number):
        host = nc.get_node_model(nc.neo4jdb, item['host_handle_id'])
        age = helpers.neo4j_report_age(host.data, 15, 30)
        operational_state = host.data.get('operational_state', 'Not set')
        host_type = host.meta_type
        host_user = item['host_user_name']
        uptime = host.data.get('uptime', '')
        if uptime:
            uptime = timestamp_to_td(uptime).days
        if host_type == 'Logical' and age != 'very_old' and operational_state != 'Decommissioned':
            values = [
                unicode(host_user),
                unicode(host.data['name']),
                unicode(host_type).capitalize(),
                u', '.join([address for address in host.data['ip_addresses']]),
                unicode(host.data['contract_number']),
                unicode(host.data.get('description', '')),
                unicode(host.data.get('responsible_group', '')),
                unicode(host.data.get('backup', 'Not set')),
                unicode(yesno(host.data.get('syslog', None), 'Yes,No,Not set')),
                unicode(yesno(host.data.get('nagios_checks', False), 'Yes,No,Not set')),
                unicode(operational_state),
                unicode(host.data.get('security_class', '')),
                unicode(''),
                unicode(date(helpers.isots_to_dt(host.data), "Y-m-d")),
                unicode(uptime),
            ]
            result.append(dict(zip(header, values)))
    num_hosts = len(result)
    filename = '%s hosts %s.xls' % (contract_number, last_month.strftime('%B %Y'))
    wb = helpers.dicts_to_xls(result, header, contract_number)
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
        msg = helpers.create_email(subject, body, extended_to, cc, bcc, temp.read(), filename, 'application/excel')
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
        monthly_dict = json.loads(service_node.data.get('netapp_storage_monthly', '{}'))
        monthly_dict.setdefault(str(last_month.year), {})[str(last_month.month)] = \
            service_node.data.get('netapp_storage_sum', 0.0)
        property_dict = {'netapp_storage_monthly': json.dumps(monthly_dict)}
        helpers.dict_update_node(user, service_node.handle_id, property_dict, property_dict.keys())
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
        customers = [item['node'].data.get('name', '') for item in service_node.get_customers().get('customers', [])]
        customers = ', '.join(customers)
        data_dict = json.loads(service_node.data.get('netapp_storage_monthly', '{}')).get(year, None)
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
            wb = helpers.dicts_to_xls({}, [], '%s Q%d %s' % (service['service_id'], last_quarter, year))
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
                msg = helpers.create_email(subject, body, extended_to, cc, bcc, temp.read(), filename, 'application/excel')
                msg.send()
    return HttpResponse('Quarterly NetApp storage reports sent!')


@login_required
def unique_ids(request, organisation=None):
    if not organisation:
        return render_to_response('noclook/reports/unique_ids/choose_organization.html', {}, context_instance=RequestContext(request))
    if organisation == 'NORDUnet':
        id_list = get_id_list(request.GET or None)
        id_list = paginate(id_list, request.GET.get('page'))
    else:
        raise Http404
    search_form = SearchIdForm(request.GET or None)
    return render_to_response('noclook/reports/unique_ids/list.html',
        {'id_list': id_list, 'organisation': organisation, 'search_form': search_form},
        context_instance=RequestContext(request))

@login_required
def download_unique_ids(request, organisation=None, file_format=None):
    header = ["ID", "Reserved", "Reserve message", "Reserver", "Created"]

    if organisation == 'NORDUnet':
        id_list = get_id_list(request.GET or None)
        create_dict = lambda uid : {'ID': uid.unique_id, 'Reserve message': uid.reserve_message, 'Reserved': uid.reserved, 'Reserver': str(uid.reserver), 'Created': uid.created}
        table = [ create_dict(uid)  for uid in id_list]
        # using values is faster, a lot, but no nice header :( and no username
        #table = id_list.values()
    if table and file_format == 'xls':  
        return helpers.dicts_to_xls_response(table, header)
    elif table and file_format == 'csv':
        return helpers.dicts_to_csv_response(table, header)
    else:
        raise Http404

def paginate(full_list, page=None):
    paginator = Paginator(full_list, 250, allow_empty_first_page=True)
    try:
        paginated_list = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        paginated_list = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        paginated_list = paginator.page(paginator.num_pages)
    return paginated_list
  
def get_id_list(data=None):
    id_list = NordunetUniqueId.objects.all().prefetch_related('reserver')
    form = SearchIdForm(data)
    if form.is_valid():
        #do stuff
        if form.cleaned_data['reserved'] != None:
            id_list = id_list.filter(reserved=form.cleaned_data['reserved'])
        if form.cleaned_data['reserve_message']:
            id_list = id_list.filter(reserve_message__icontains=form.cleaned_data['reserve_message'])
        id_list = id_list.filter(unique_id__startswith=form.cleaned_data['id_type'])
    return id_list.order_by('created').reverse()
