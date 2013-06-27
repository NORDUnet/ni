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

import norduni_client as nc

q = """
    START unit = node:node_types("node_type:Unit")
    return unit
    """

with nc.neo4jdb.transaction:
    for hit in nc.neo4jdb.query(q):
        hit['unit']['name'] = str(hit['unit']['name'])
        print '.',

print "done."


