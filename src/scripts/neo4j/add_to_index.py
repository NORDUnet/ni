# -*- coding: utf-8 -*-
"""
Created on Tue Jul  5 15:39:31 2011

@author: lundberg
"""

'''
Add nodes which has the supplied property/key to the index with the name 
supplied.
'''

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

import norduni_client as nc

# User friendly usage output
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--index', nargs='?', help='Index name.')
parser.add_argument('-p', '--property', nargs='?', help='Node property/key \
whose value you want to add for all nodes.')
parser.add_argument('-l', '--list', action='store_true',
    help='List available indexes.')
args = parser.parse_args()

if args.list:
    print 'Available indexes:'
    for i in nc.get_all_node_indexes().keys():
        print i
    sys.exit(0)

if args.index and args.property:
    for node in nc.get_all_nodes():
        added = nc.add_index_node(args.index, args.property, node.id)
        if added:
            print 'Node(%d), \'%s\' = \'%s\', added to index %s' % (node.id,
                                                        args.property,
                                                        node[args.property],
                                                        args.index)
        else:
            print 'Node(%d) NOT added to index %s' % (node.id, args.index)
else:
    parser.print_help()

