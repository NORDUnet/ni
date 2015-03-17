# -*- coding: utf-8 -*-
"""
Created on Thu Oct 13 16:36:31 2011

@author: lundberg
"""

from neo4j import IntegrityError, ProgrammingError, InternalError
from socket import error as SocketError
import core


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
            meta_type=core.get_node_meta_type(self.manager, self.handle_id1), handle_id=self.handle_id1)
        node2_str = '{meta_type} Node ({handle_id})'.format(
            meta_type=core.get_node_meta_type(self.manager, self.handle_id2), handle_id=self.handle_id2)
        return '%s %s %s is not possible.' % (node1_str, self.relationship_type,
                                              node2_str)                       


class MetaLabelNamingError(Exception):
    """
    Exception that explains that meta labels must have special names defined
    in create_node().
    """
    def __init__(self, name):
        self.error = 'A meta label can not be named {name}.'.format(name=name)
        
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


class BadProperties(Exception):
    """
    If a user tries to set node or relationship properties that are not Numeric values,
    String values or Boolean values.
    """
    def __init__(self, properties):
        self.properties = properties

    def __str__(self):
        return '''Tried to set {properties} as properties.
Only numeric values, string values or boolean values are allowed'''.format(properties=self.properties)


class NodeNotFound(Exception):
    """
    The provided handle_id did not match any node in the graph database.
    """
    def __init__(self, manager, handle_id):
        self.message = '{handle_id} did not match a node in database at {db}.'.format(handle_id=handle_id,
                                                                                      db=manager.dsn)

    def __str__(self):
        return self.message


class RelationshipNotFound(Exception):
    """
    The provided handle_id did not match any node in the graph database.
    """
    def __init__(self, manager, relationship_id):
        self.message = '{relationship_id} did not match a relationship in database at {db}.'.format(
            relationship_id=relationship_id, db=manager.dsn)

    def __str__(self):
        return self.message