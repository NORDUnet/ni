# -*- coding: utf-8 -*-
"""
Created on 2012-06-11 5:48 PM

@author: lundberg
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import Http404
import tempfile
from datetime import datetime
from django.conf import settings as django_settings

from niweb.apps.noclook.forms import get_node_type_tuples
from niweb.apps.noclook.models import NordunetUniqueId
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


def mail_host_contract_report(auth_key, contract_number):
    """
    :param auth_key: String
    :param contract_number: String
    :return: None

    Sends mail to addresses specified in settings.REPORTS_TO with reports attached.
    """
    subject = 'NOCLook host report for %s' % contract_number
    to = getattr(django_settings, 'REPORTS_TO', [])
    body = '''
        An auto generated report from NOCLook regarding contract number %s.

        This report was generated %s UTC.
        ''' % (contract_number, datetime.utcnow())
    filename = 'contract_number_%s.xls' % contract_number

    header = [
        'Host user',
        'Host',
        'Host type',
        'IP address(es)',
        'Contract number',
        'Description',
        'Backup',
        'Responsible',
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
        # TODO: Filter hosts found
        values = [
            unicode(hit['host_user']['name']),
            unicode(hit['host']['name']),
            unicode(hit['host_type']),
            u', '.join([address for address in hit['host']['ip_addresses']]),
            unicode(hit['host']['contract_number']),
            unicode(hit['host'].get_property('description', '')),
            unicode(hit['host'].get_property('responsible_group', '')),
            unicode(hit['host'].get_property('backup', 'Not set')),
            unicode(hit['host'].get_property('syslog', 'Not set')),
            unicode('Nagios'),
            unicode(hit['host'].get_property('operational_state', 'Not set')),
            unicode(hit['host'].get_property('security_class', '')),
            unicode('Location'),
            unicode('Last Seen'),
            unicode('Uptime'),
        ]
        result.append(dict(zip(header, values)))
    wb = h.dicts_to_xls(result, header, contract_number)
    with tempfile.TemporaryFile() as temp:
        wb.save(temp)
        temp.seek(0)
        msg = h.create_email(subject, body, to, temp.read(), filename, 'application/excel')
        msg.send()
    return None




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