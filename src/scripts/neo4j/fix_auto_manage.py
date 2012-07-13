# -*- coding: utf-8 -*-
"""
Created on 2012-07-10 11:07 AM

@author: lundberg
"""

# Use this script to remove all auto_manage properties that was set to False due to a neo4j bug.
# As missing property is equal to False when NOCLook is concerned all nodes will have the right
# value after the next consume.

import sys
import os

path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from apps.noclook import helpers as h
import norduni_client as nc

print "Deleting property from nodes.",
for node in nc.neo4jdb.nodes:
    if node.getProperty('noclook_auto_manage', False):
        with nc.neo4jdb.transaction:
            del node['noclook_auto_manage']
            print '.',
print "done."

print "Deleting property from relationships.",
for rel in nc.neo4jdb.relationships:
    if rel.getProperty('noclook_auto_manage', False):
        with nc.neo4jdb.transaction:
            del rel['noclook_auto_manage']
            print '.',
print "done."


