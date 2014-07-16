# -*- coding: utf-8 -*-
"""
Created on 2012-11-28 4:45 PM

@author: lundberg
"""

# Set all Hosts, Hosts Services and relationships between them to auto managed and set a last
# seen value if missing.

import sys
import os

## Need to change this path depending on where the Django project is
## located.
#path = '/var/norduni/src/niweb/'
path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import norduniclient as nc

q1 = """
    START host = node:node_types(node_type = "Host")
    MATCH host<-[r?:Depends_on]-service
    SET host.noclook_auto_manage = true
    WITH host
    WHERE not(has(host.noclook_last_seen))
    SET host.noclook_last_seen = "2012-01-19T00:00:00.000000"
    """

for hit in nc.neo4jdb.query(q1):
    pass

q2 = """
    START host = node:node_types(node_type = "Host")
    MATCH host<-[r:Depends_on]-service
    WHERE service.node_type = "Host Service"
    SET r.noclook_auto_manage = true
    WITH r
    WHERE not(has(r.noclook_last_seen))
    SET r.noclook_last_seen = "2012-01-19T00:00:00.000000"
    """

for hit in nc.neo4jdb.query(q2):
    pass

q3 = """
    START service = node:node_types(node_type = "Host Service")
    SET service.noclook_auto_manage = true
    WITH service
    WHERE not(has(service.noclook_last_seen))
    SET service.noclook_last_seen = "2012-01-19T00:00:00.000000"
    """

for hit in nc.neo4jdb.query(q3):
    pass

print "Done!"