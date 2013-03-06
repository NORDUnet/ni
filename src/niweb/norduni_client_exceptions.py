# -*- coding: utf-8 -*-
"""
Created on Thu Oct 13 16:36:31 2011

@author: lundberg
"""
import norduni_client as nc

class NoRelationshipPossible(Exception):
    """
    Exception that explains why the nodes relationship was not possible.
    """
    def __init__(self, node1, node2, relationship_type):
        self.node1 = node1
        self.node2 = node2
        self.relationship_type = relationship_type
    
    def __str__(self):
        node1_str = '%s node %s (%d)' % (nc.get_node_meta_type(self.node1), 
                                    self.node1['name'], self.node1.getId())
        node2_str = '%s node %s (%d)' % (nc.get_node_meta_type(self.node2), 
                                    self.node2['name'], self.node2.getId())
        return '%s %s %s is not possible.' % (node1_str, self.relationship_type,
                                              node2_str)                       

class MetaNodeNamingError(Exception):
    """
    Exception that explains that meta nodes must have special names defined
    in create_meta_node().
    """
    def __init__(self, names):
        self.error = 'A meta node can not have that name.'
        
    def __str__(self):
        return self.error


class NoMetaNodeFound(Exception):
    """
    All nodes need a meta type to function correctly in the NOCLook model. This
    exception should be raised if the nodes meta node can't be found.
    """
    def __init__(self, node):
        self.node = node
        
    def __str__(self):
        return 'Node %s (%d) has no meta node.' % (self.node['name'], self.node.getId())


class UniqueNodeError(Exception):
    """
    Should be raised when the user tries to create a new node that should be
    unique for that node_name and node_type.
    """
    def __init__(self, node):
        self.node = node

    def __str__(self):
        return 'A node named %s (%d) with node type %s already exists.' % (self.node['name'],
                                                                           self.node.getId(),
                                                                           self.node['node_type'])