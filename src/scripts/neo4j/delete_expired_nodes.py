# -*- coding: utf-8 -*-
"""
Created on 2013-01-25 10:46 AM

@author: lundberg

This script will delete all nodes of the supplied node type that are older than
settings.NEO4J_MAX_AGE.
"""

import sys
import os
import argparse

## Need to change this path depending on where the Django project is
## located.
#path = '/var/norduni/src/niweb/'
path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import apps.noclook.helpers as h
import norduniclient as nc

# User friendly usage output
parser = argparse.ArgumentParser()
parser.add_argument('-t', '--type', nargs='?', help='Node type (case sensitive).')
parser.add_argument('-d', '--delete', action='store_true', default=False, help='Actually delete the nodes.')
parser.add_argument('-f', '--force', action='store_true', default=False,
                    help='Delete expired nodes even if they are not auto managed.')
args = parser.parse_args()

node_type = args.type
delete = args.delete
force = args.force

if not node_type:
    print 'No node type set. Set node type with -t [node type].'
    sys.exit(0)

q = """
    START node=node:node_types(node_type='%s')
    WHERE node.noclook_auto_manage! = true
    RETURN node
    """ % node_type

for hit in nc.neo4jdb.query(q):
    last_seen, expired = h.neo4j_data_age(hit['node'])
    if expired:
        if delete:
            pass # TODO: Revisit when running neo4j 1.9
        else:
            print '%s %s would be deleted.' % (hit['node']['node_type'], hit['node']['name'])
            print 'Last seen: %s' % hit['node']['noclook_last_seen']

