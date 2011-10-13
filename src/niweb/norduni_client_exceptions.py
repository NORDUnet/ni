# -*- coding: utf-8 -*-
"""
Created on Thu Oct 13 16:36:31 2011

@author: lundberg
"""

import norduni_client as nc

class NoRelationshipPossible(Exception):
    '''
    Exception that explains why the nodes relationship was not possible.
    '''
    def __init__(self, node1, node2, relationship_type):
        self.node1 = node1
        self.node2 = node2
        self.relationship_type = relationship_type
    
    def __str__(self):
        node1_str = '%s node %s' % (nc.get_node_meta_type(self.node1), 
                                    self.node1['name'])
        node2_str = '%s node %s' % (nc.get_node_meta_type(self.node2), 
                                    self.node2['name'])
        return '%s %s %s is not possible.' % (node1_str, self.relationship_type,
                                              node2_str)                       
        