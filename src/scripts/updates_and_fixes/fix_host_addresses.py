# -*- coding: utf-8 -*-
"""
Created on 2012-07-10 11:41 AM

@author: lundberg
"""


# Host IP addresses property should be called ip_addresses.

import sys
import os

path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import norduni_client as nc

node_types_index = nc.get_node_index(nc.neo4jdb, 'node_types')
hits = node_types_index['node_type']['Host']

for hit in hits:

    addresses = hit.get_property('addresses', None)

    if not addresses:
        print 'Node %d: %s does not have a cable type.' % (hit.getId(), hit.getProperty('name'))
    else:
        with nc.neo4jdb.transaction:
            hit.set_property('ip_addresses', addresses)
            del hit['addresses']
    print 'Node %d: %s done.' % (hit.getId(), hit.getProperty('name'))


