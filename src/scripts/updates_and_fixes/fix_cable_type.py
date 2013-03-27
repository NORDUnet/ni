# -*- coding: utf-8 -*-
"""
Created on 2012-07-10 11:41 AM

@author: lundberg
"""


# Cable type Fiber has changed to Dark Fiber and TP to Patch

import sys
import os

path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from apps.noclook.models import NodeHandle
import norduni_client as nc

node_types_index = nc.get_node_index(nc.neo4jdb, 'node_types')
hits = node_types_index['node_type']['Cable']

for hit in hits:
    try:
        cable_type = hit['cable_type']
    except KeyError:
        print 'Node %d: %s does not have a cable type.' % (hit.getId(),
                                                             hit.getProperty('name'))
        continue
    with nc.neo4jdb.transaction:
        if cable_type == "Fiber":
            hit.setProperty('cable_type', 'Dark Fiber')
        elif cable_type == "TP":
            hit.setProperty('cable_type', 'Patch')
    print 'Node %d: %s done.' % (hit.getId(), hit.getProperty('name'))


