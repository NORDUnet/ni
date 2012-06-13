# -*- coding: utf-8 -*-
"""
Created on 2012-06-11 5:48 PM

@author: lundberg
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext

from niweb.apps.noclook.forms import get_node_type_tuples
from niweb.apps.noclook.helpers import nodes_to_csv, nodes_to_xls
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
            MATCH node-[r:Uses|Owns]->host
            RETURN node.name as host_user, host, host.name as host_name, host.noclook_last_seen as last_seen
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
                MATCH host<-[r?:Uses|Owns]-()
                WHERE r is null
                RETURN host, host.name as host_name, host.noclook_last_seen as last_seen
                '''
        hosts = nc.neo4jdb.query(hosts_q, id=host_user_id)
    elif host_user_name == 'All':
        num_of_hosts_q = '''
                START node=node:node_types(node_type = "Host User")
                MATCH node-[r:Uses|Owns]->host
                RETURN COUNT(node) as num_of_hosts
                '''
        num_of_hosts_hits = nc.neo4jdb.query(num_of_hosts_q, id=host_user_id)
        num_of_hosts = [hit['num_of_hosts'] for hit in num_of_hosts_hits][0]
        hosts_q = '''
                START node=node:node_types(node_type = "Host User")
                MATCH node-[r:Uses|Owns]->host
                RETURN node.name as host_user, host, host.name as host_name, host.noclook_last_seen as last_seen
                '''
        hosts = nc.neo4jdb.query(hosts_q, id=host_user_id)
    if form:
        header = ['host_user', 'host_name', 'last_seen']
        if form == 'csv':
            return nodes_to_csv([host for host in hosts], header=header)
        elif form == 'xls':
            return nodes_to_xls([host for host in hosts], header=header)
    return render_to_response('noclook/reports/host-users.html',
            {'host_user_name': host_user_name, 'host_users': host_users,
            'num_of_hosts': num_of_hosts, 'hosts': hosts},
            context_instance=RequestContext(request))