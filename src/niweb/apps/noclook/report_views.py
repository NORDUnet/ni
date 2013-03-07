# -*- coding: utf-8 -*-
"""
Created on 2012-06-11 5:48 PM

@author: lundberg
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import Http404

from niweb.apps.noclook.forms import get_node_type_tuples
from niweb.apps.noclook.helpers import nodes_to_csv, nodes_to_xls
from niweb.apps.noclook.models import NordunetUniqueId
import norduni_client as nc

@login_required
def host_reports(request):
    return render_to_response('noclook/reports/host_reports.html',{},
                              context_instance=RequestContext(request))

@login_required
def host_users(request, host_user_name=None, form=None):
    host_users = dict([[name,id] for id,name in get_node_type_tuples('Host User') if name])
    hosts = []
    num_of_hosts = 0
    host_user_id = host_users.get(host_user_name, None)
    if host_user_id:
        num_of_hosts_q = '''
            START node=node({id})
            MATCH node-[r:Uses|Owns]->host
            RETURN COUNT(host) as num_of_hosts
            '''
        num_of_hosts_hits = nc.neo4jdb.query(num_of_hosts_q, id=host_user_id)
        num_of_hosts = [hit['num_of_hosts'] for hit in num_of_hosts_hits][0]
        hosts_q = '''
            START node=node({id})
            MATCH node-[r:Uses|Owns]->host<-[:Contains]-meta
            RETURN node.name as host_user, host, host.name as host_name,
            host.noclook_last_seen as last_seen, meta.name as meta
            '''
        hosts = nc.neo4jdb.query(hosts_q, id=host_user_id)
    elif host_user_name == 'Missing':
        num_of_hosts_q = '''
                START host=node:node_types(node_type = "Host")
                MATCH host<-[r?:Uses|Owns]-()
                WHERE r is null
                RETURN COUNT(host) as num_of_hosts
                '''
        num_of_hosts_hits = nc.neo4jdb.query(num_of_hosts_q, id=host_user_id)
        num_of_hosts = [hit['num_of_hosts'] for hit in num_of_hosts_hits][0]
        hosts_q = '''
                START host=node:node_types(node_type = "Host")
                MATCH meta-[:Contains]->host<-[r?:Uses|Owns]-()
                WHERE r is null
                RETURN host, host.name as host_name, host.noclook_last_seen as last_seen,
                meta.name as meta
                '''
        hosts = nc.neo4jdb.query(hosts_q, id=host_user_id)
    elif host_user_name == 'All':
        num_of_hosts_q = '''
                START node=node:node_types(node_type = "Host User")
                MATCH node-[r:Uses|Owns]->host
                RETURN COUNT(node) as num_of_hosts
                '''
        num_of_hosts_hits = nc.neo4jdb.query(num_of_hosts_q)
        num_of_hosts = [hit['num_of_hosts'] for hit in num_of_hosts_hits][0]
        hosts_q = '''
                START node=node:node_types(node_type = "Host User")
                MATCH node-[r:Uses|Owns]->host<-[:Contains]-meta
                RETURN node.name as host_user, host, host.name as host_name,
                host.noclook_last_seen as last_seen, meta.name as meta
                '''
        hosts = nc.neo4jdb.query(hosts_q)
    if form:
        header = ['host_user', 'host_name', 'last_seen']
        if form == 'csv':
            return nodes_to_csv([host for host in hosts], header=header)
        elif form == 'xls':
            return nodes_to_xls([host for host in hosts], header=header)
    return render_to_response('noclook/reports/host_users.html',
            {'host_user_name': host_user_name, 'host_users': host_users,
            'num_of_hosts': num_of_hosts, 'hosts': hosts},
            context_instance=RequestContext(request))

@login_required
def host_security_class(request, status=None, form=None):
    num_of_hosts = 0
    hosts = []
    if status == 'all':
        num_of_hosts_q = '''
                START node=node:node_types(node_type = "Host")
                RETURN COUNT(node) as num_of_hosts
                '''
        num_of_hosts_hits = nc.neo4jdb.query(num_of_hosts_q)
        num_of_hosts = [hit['num_of_hosts'] for hit in num_of_hosts_hits][0]
        hosts_q = '''
                START node=node:node_types(node_type = "Host")
                RETURN node, node.name as host_name,
                node.description? as description,
                node.security_class? as security_class,
                node.security_comment? as security_comment,
                node.noclook_last_seen as last_seen
                '''
        hosts = nc.neo4jdb.query(hosts_q)
    elif status == 'classified':
        num_of_hosts_q = '''
                START node=node:node_types(node_type = "Host")
                WHERE has(node.security_class)
                RETURN COUNT(node) as num_of_hosts
                '''
        num_of_hosts_hits = nc.neo4jdb.query(num_of_hosts_q)
        num_of_hosts = [hit['num_of_hosts'] for hit in num_of_hosts_hits][0]
        hosts_q = '''
                START node=node:node_types(node_type = "Host")
                WHERE has(node.security_class)
                RETURN node, node.name as host_name,
                node.description? as description,
                node.security_class? as security_class,
                node.security_comment? as security_comment,
                node.noclook_last_seen as last_seen
                '''
        hosts = nc.neo4jdb.query(hosts_q)
    elif status == 'not-classified':
        num_of_hosts_q = '''
                    START node=node:node_types(node_type = "Host")
                    WHERE not(has(node.security_class))
                    RETURN COUNT(node) as num_of_hosts
                    '''
        num_of_hosts_hits = nc.neo4jdb.query(num_of_hosts_q)
        num_of_hosts = [hit['num_of_hosts'] for hit in num_of_hosts_hits][0]
        hosts_q = '''
                    START node=node:node_types(node_type = "Host")
                    WHERE not(has(node.security_class))
                    RETURN node, node.name as host_name,
                    node.description? as description,
                    node.security_class? as security_class,
                    node.security_comment? as security_comment,
                    node.noclook_last_seen as last_seen
                    '''
        hosts = nc.neo4jdb.query(hosts_q)
    if form:
        header = ['host_name', 'description', 'security_class', 'security_comment', 'last_seen']
        if form == 'csv':
            return nodes_to_csv([host for host in hosts], header=header)
        elif form == 'xls':
            return nodes_to_xls([host for host in hosts], header=header)
    return render_to_response('noclook/reports/host_security_class.html',
        {'status': status, 'num_of_hosts': num_of_hosts, 'hosts': hosts},
        context_instance=RequestContext(request))

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