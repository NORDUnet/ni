# -*- coding: utf-8 -*-
"""
Created on 2012-10-25 5:12 PM

@author: lundberg
"""

import sys
import os
import argparse

## Need to change this path depending on where the Django project is
## located.
#path = '/var/opt/norduni/src/niweb/'
#path = '/opt/norduni/src/niweb/'
path = '/home/lundberg/norduni/src/niweb/'
##
##

sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from apps.noclook import helpers as h
import norduni_client as nc

def run():
    """
    One off function to fix missing service relationships to service components.
    """
    q = '''
        START node=node(*)
        WHERE node.node_type? = "Service" and has(node.service_component)
        WITH node
        WHERE node.service_component =~ 'NU-4.*'
        RETURN node, node.service_component as service_component
        '''

    i = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
    for hit in nc.neo4jdb.query(q):
        try:
            comp = h.iter2list(i['nordunet_id'][hit['service_component']])[0]
            if not nc.get_relationships(hit['node'], comp, 'Depends_on'):
                nc.create_relationship(nc.neo4jdb, hit['node'], comp, 'Depends_on')
                print '%s depends on %s' % (hit['node']['name'], comp['name'])
        except IndexError:
            pass

def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-R', action='store_true',
        help='Run script.')
    args = parser.parse_args()
    if not args.R:
        print 'Are you sure you want to run this script? If you are use -R as argument.'
        sys.exit(1)
    else:
        run()

if __name__ == '__main__':
    main()