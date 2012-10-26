# -*- coding: utf-8 -*-
"""
Created on 2012-10-25 5:12 PM

@author: lundberg
"""

import norduni_client as nc
import apps.noclook.helpers as h

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
