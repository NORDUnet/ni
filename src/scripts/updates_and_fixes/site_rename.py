# -*- coding: utf-8 -*-
"""
Created on 2012-05-22 3:24 PM

@author: lundberg
"""

'''
Use this script to add the country code to the site name.
'''
import sys
import os

path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from apps.noclook.models import NodeHandle
import norduniclient as nc

node_types_index = nc.get_node_index(nc.neo4jdb, 'node_types')
hits = node_types_index['node_type']['Site']

for hit in hits:
    try:
        cc = hit['country_code']
    except KeyError:
        print 'Node %d: %s does not have a country code.' % (hit.getId(),
                                                             hit.getProperty('name'))
        continue
    with nc.neo4jdb.transaction:
        name = hit.getProperty('name')
        name = '%s-%s' % (cc, name)
        hit.setProperty('name', name)
        index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
        nc.update_index_item(nc.neo4jdb, index, hit, 'name')
        nh = NodeHandle.objects.get(pk=int(hit['handle_id']))
        nh.node_name = name
        nh.save()
    print 'Node %d: %s done.' % (hit.getId(), hit.getProperty('name'))


