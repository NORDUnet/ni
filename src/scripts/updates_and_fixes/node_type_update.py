# -*- coding: utf-8 -*-
"""
Created on Wed May  4 13:36:24 2011
@author: lundberg

This will change all nodes type property to node_type. Needed when upgrading
to commit a59a3cb913956efd8d7a7b02664d8ec919752531 or above.
"""

import norduni_client as nc

all_nodes = nc.get_all_nodes()

for n in all_nodes:
    try:
        n['node_type'] = n['type']
        del n['type']
    except KeyError:
        pass
print 'node[\'type\'] is now node[\'node_type\']'