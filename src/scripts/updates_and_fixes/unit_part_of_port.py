# -*- coding: utf-8 -*-
"""
Created on 2012-11-28 4:45 PM

@author: lundberg
"""

# Changes all Depends_on relationships between Unit and Ports to Part_of relationships

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

import norduni_client as nc

q = """
    START unit = node:node_types("node_type:Unit")
    MATCH unit-[r:Depends_on]->port
    WITH unit,r,port,r.noclook_auto_manage as auto
    DELETE r
    CREATE unit-[r2:Part_of {noclook_auto_manage: auto}]->port
    return r2
    """

for hit in nc.neo4jdb.query(q):
    print hit['r2']