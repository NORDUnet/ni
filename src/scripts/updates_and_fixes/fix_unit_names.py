# -*- coding: utf-8 -*-
"""
Created on 2013-06-27 10:43 AM

@author: lundberg
"""

# Unit names have become a mix of Strings and Longs, unknown why. This scrip will
# set the name to a string.

import sys
import os

path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from apps.noclook.helpers import update_node_search_index
import norduni_client as nc

q = """
    START unit = node:node_types("node_type:Unit")
    return unit
    """

with nc.neo4jdb.transaction:
    for hit in nc.neo4jdb.query(q):
        node = hit['unit']
        node['name'] = str(hit['unit']['name'])
        update_node_search_index(nc.neo4jdb, node)
        print '.',

print "done."


