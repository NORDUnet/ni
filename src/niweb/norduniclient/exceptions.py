# -*- coding: utf-8 -*-
"""
Created on Thu Oct 13 16:36:31 2011

@author: lundberg
"""
import norduniclient as nc


class NoRelationshipPossible(Exception):
    """
    Exception that explains why the nodes relationship was not possible.
    """
    def __init__(self, manager, handle_id1, handle_id2, relationship_type):
        self.manager = manager
        self.handle_id1 = handle_id1
        self.handle_id2 = handle_id2
        self.relationship_type = relationship_type
    
    def __str__(self):
        node1_str = '{meta_type} Node ({handle_id})'.format(
            meta_type=nc.get_node_meta_type(self.manager, self.handle_id1), handle_id=self.handle_id1)
        node2_str = '{meta_type} Node ({handle_id})'.format(
            meta_type=nc.get_node_meta_type(self.manager, self.handle_id2), handle_id=self.handle_id2)
        return '%s %s %s is not possible.' % (node1_str, self.relationship_type,
                                              node2_str)                       


class MetaLabelNamingError(Exception):
    """
    Exception that explains that meta labels must have special names defined
    in create_node().
    """
    def __init__(self):
        self.error = 'A meta node can not have that name.'
        
    def __str__(self):
        return self.error


class NoMetaLabelFound(Exception):
    """
    All nodes need a meta type to function correctly in the NOCLook model. This
    exception should be raised if the nodes meta node can't be found.
    """
    def __init__(self, handle_id):
        self.handle_id = handle_id
        
    def __str__(self):
        return 'Node with handle_id {handle_id} has no meta label.'.format(handle_id=self.handle_id)


class UniqueNodeError(Exception):
    """
    Should be raised when the user tries to create a new node that should be
    unique for that node_name and node_type.
    """
    def __init__(self, name, handle_id, node_type):
        self.name = name
        self.handle_id = handle_id
        self.node_type = node_type

    def __str__(self):
        return 'A node named {name} with node type {type} already exists. Handle ID: {id}'.format(name=self.name,
                                                                                                  type=self.node_type,
                                                                                                  id=self.handle_id)


class MultipleNodesReturned(Exception):
    """
    If a user requests an unique node, by name and type, and multiple nodes are returned
    this exception should be raised.
    """
    def __init__(self, node_name, node_type):
        self.node_name = node_name
        self.node_type = node_type

    def __str__(self):
        return 'Multiple nodes of name %s and type %s was returned.' % (self.node_name,
                                                                        self.node_type)