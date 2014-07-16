# -*- coding: utf-8 -*-
#
#       core.py
#
#       Copyright 2011 Johan Lundberg <lundberg@nordu.net>
#

# This started as an extension to the Neo4j REST client made by Versae, continued
# as an extension for the official Neo4j python bindings when they were released
# (Neo4j 1.5, python-embedded).
#
# After the python-embedded drivers where discontinued with Neo4j 2.0 we are now
# using neo4jdb-python transaction endpoint drivers.
#
# The goal is to make it easier to add and retrieve data from a Neo4j database
# according to the NORDUnet Network Inventory data model.
#
# More information about NORDUnet Network Inventory:
# https://portal.nordu.net/display/NI/

from __future__ import absolute_import

from .exceptions import *
from .helpers import *
import re
from neo4j import contextmanager, IntegrityError, ProgrammingError

# Load Django settings
try:
    from django.core.exceptions import ImproperlyConfigured
    from django.conf import settings as django_settings
    NEO4J_URI = django_settings.NEO4J_RESOURCE_URI
except (ImportError, ImproperlyConfigured):
    NEO4J_URI = None
    print 'Starting up without a Django environment.'
    print 'Initial: norduniclient.neo4jdb == None.'
    print 'Use norduniclient.init_db(uri) to open a database connection.'


META_TYPES = ['Physical', 'Logical', 'Relation', 'Location']


def init_db(uri=NEO4J_URI):
    if uri:
        manager = _get_db_manager(uri)
        try:
            with manager.transaction as w:
                w.execute('CREATE CONSTRAINT ON (n:Node) ASSERT n.handle_id IS UNIQUE')
        except IntegrityError:
            pass
        try:
            with manager.transaction as w:
                w.execute('CREATE INDEX ON :Node(name)')
        except IntegrityError:
            pass
        return manager


def _get_db_manager(uri):
    return contextmanager.Neo4jDBConnectionManager(uri)


def create_node(manager, name, meta_type_label, type_label, handle_id):
    """
    Creates a node with the mandatory attributes name and handle_id also sets type label.

    :param manager: Neo4jDBConnectionManager
    :param name: string
    :param type_label: string
    :param handle_id: Unique id
    :return: None
    """
    if meta_type_label not in META_TYPES:
        raise MetaLabelNamingError
    q = """
        CREATE (n:Node:%s:%s { name: { name }, handle_id: { handle_id }})
        RETURN n
        """ % (meta_type_label, type_label)
    with manager.transaction as w:
        return w.execute(q, name=name, handle_id=handle_id).fetchall()[0][0]
    

def get_node(manager, handle_id):
    """
     :param manager: Neo4jDBConnectionManager
    :param handle_id: Unique id
    :return: dict
    """
    q = 'MATCH (n:Node { handle_id: {handle_id} }) RETURN n'
    try:
        with manager.read as r:
            return r.execute(q, handle_id=handle_id).fetchall()[0][0]
    except IndexError:
        return None


def delete_node(manager, handle_id):
    """
    Deletes the node and all its relationships.

    :param manager: Neo4jDBConnectionManager
    :param handle_id: Unique id
    :return: bool
    """
    q = 'MATCH (n:Node { handle_id: {handle_id} })-[r]-() DELETE n,r'
    with manager.transaction as t:
        t.execute(q, handle_id=handle_id)
    return True


def get_relationship(manager, relationship_id):
    """
     :param manager: Neo4jDBConnectionManager
    :param relationship_id: Internal Neo4j id
    :return: dict
    """
    q = 'START r=relationship({relationship_id}) RETURN r'
    try:
        with manager.read as r:
            return r.execute(q, relationship_id=relationship_id).fetchall()[0][0]
    except IndexError:
        return None


def delete_relationship(manager, relationship_id):
    """
    Deletes the relationship.

    :param manager:  Neo4jDBConnectionManager
    :param relationship_id: Internal Neo4j relationship id
    :return: bool
    """
    q = 'START r=relationship({relationship_id}) DELETE r'
    with manager.transaction as t:
        t.execute(q, relationship_id=relationship_id)
    return True


def get_node_meta_type(manager, handle_id):
    """
    Returns the meta type of the supplied node as a string.

    :param manager: Neo4jDBConnectionManager
    :param handle_id: Unique id
    :return: string
    """
    q = '''
        MATCH (n:Node { handle_id: {handle_id} })
        RETURN labels(n)
        '''

    with manager.read as r:
        labels, = r.execute(q, handle_id=handle_id).fetchone()
        for label in labels:
            if label in META_TYPES:
                return label
    raise NoMetaLabelFound(handle_id)


# TODO: Try out elasticsearch
def get_node_by_value(manager, value, prop=None, node_type="Node"):
    """
    Traverses all nodes or nodes of specified label and compares the property/properties of the node
    with the supplied string.

    :param manager: Neo4jDBConnectionManager
    :param value: string
    :param prop: string
    :param node_type:
    :return: dicts
    """
    if prop:
        q = '''
            MATCH (n:{label})
            USING SCAN n:{label}
            WHERE n.{prop} =~ "(?i).*{value}.*"
            RETURN distinct n
            '''.format(label=node_type, prop=prop, value=value)
        try:
            with manager.read as r:
                for node, in r.execute(q):
                    yield node
        except ProgrammingError:  # Can't do regex on int. bool or lists
            q = '''
                MATCH (n:{label})
                USING SCAN n:{label}
                WHERE HAS(n.{prop})
                RETURN n
                '''.format(label=node_type, prop=prop)
            pattern = re.compile('.*{0}.*'.format(value), re.IGNORECASE)
            with manager.read as r:
                for node, in r.execute(q):
                    if pattern.match(unicode(node.get(prop, None))):
                        yield node
    else:
        q = '''
            MATCH (n:{label})
            RETURN n
            '''.format(label=node_type)
        pattern = re.compile('.*{0}.*'.format(value), re.IGNORECASE)
        with manager.read as r:
            for node, in r.execute(q):
                for v in node.values():
                    if pattern.match(unicode(v)):
                        yield node
                        break


def get_unique_node_by_name(manager, node_name, node_type):
    """
    Returns the node if the node is unique for name and type or None.

    :param manager:  Neo4jDBConnectionManager
    :param node_name: string
    :param node_type: string
    :return: dict
    """
    q = '''
        MATCH (n:Node { name: {name} })
        WHERE {label} IN labels(n)
        RETURN n
        '''
    with manager.read as r:
        hits = r.execute(q, name=node_name, label=node_type).fetchall()
    if hits:
        if len(hits) == 1:
            return hits[0][0]
        raise MultipleNodesReturned(node_name, node_type)
    return None


def _create_relationship(manager, handle_id, other_handle_id, rel_type):

    q = """
        MATCH (a:Node {handle_id: {start}}),(b:Node {handle_id: {end}})
        CREATE a-[r:%s]->b
        RETURN ID(r)
        """ % rel_type

    with manager.transaction as w:
        return w.execute(q, start=handle_id, end=other_handle_id).fetchall()[0][0]


def create_location_relationship(manager, location_node, other_node, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    """
    if get_node_meta_type(manager, other_node) == 'Location' and rel_type == 'Has':
        return _create_relationship(manager, location_node, other_node, rel_type)
    raise NoRelationshipPossible(manager, location_node, other_node, rel_type)


def create_logical_relationship(manager, logical_node, other_node, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    """
    other_meta_type = get_node_meta_type(manager, other_node)
    if rel_type == 'Depends_on':
        if other_meta_type == 'Logical' or other_meta_type == 'Physical':
            return _create_relationship(manager, logical_node, other_node, rel_type)
    elif rel_type == 'Part_of':
        if other_meta_type == 'Physical':
            return _create_relationship(manager, logical_node, other_node, rel_type)
    raise NoRelationshipPossible(manager, logical_node, other_node, rel_type)


def create_relation_relationship(manager, relation_node, other_node, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    """
    other_meta_type = get_node_meta_type(manager, other_node)
    if other_meta_type == 'Logical':
        if rel_type in ['Uses', 'Provides']:
            return _create_relationship(manager, relation_node, other_node, rel_type)
    elif other_meta_type == 'Location' and rel_type == 'Responsible_for':
        return _create_relationship(manager, relation_node, other_node, rel_type)
    elif other_meta_type == 'Physical':
        if rel_type in ['Owns', 'Provides']:
            return _create_relationship(manager, relation_node, other_node, rel_type)
    raise NoRelationshipPossible(manager, relation_node, other_node, rel_type)


def create_physical_relationship(manager, physical_node, other_node, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    """
    other_meta_type = get_node_meta_type(manager, other_node)
    if other_meta_type == 'Physical':
        if rel_type == 'Has' or rel_type == 'Connected_to':
            return _create_relationship(manager, physical_node, other_node, rel_type)
    elif other_meta_type == 'Location' and rel_type == 'Located_in':
        return _create_relationship(manager, physical_node, other_node, rel_type)
    raise NoRelationshipPossible(manager, physical_node, other_node, rel_type)


def create_relationship(manager, node, other_node, rel_type):
    """
    Makes a relationship from node to other_node depending on which
    meta_type the nodes are. Returns the relationship or raises
    NoRelationshipPossible exception.
    """
    meta_type = get_node_meta_type(manager, node)
    if meta_type == 'Location':
        return create_location_relationship(manager, node, other_node, rel_type)
    elif meta_type == 'Logical':
        return create_logical_relationship(manager, node, other_node, rel_type)
    elif meta_type == 'Relation':
        return create_relation_relationship(manager, node, other_node, rel_type)
    elif meta_type == 'Physical':
        return create_physical_relationship(manager, node, other_node, rel_type)
    raise NoRelationshipPossible(manager, node, other_node, rel_type)


def get_relationships(manager, handle_id1, handle_id2, rel_type=None):
    """
    Takes a start and an end node with an optional relationship
    type.
    Returns the relationships between the nodes or an empty list.
    """
    if rel_type:
        q = """
        MATCH (a:Node {{handle_id: {{handle_id1}}}})-[r:{rel_type}]-(b:Node {{handle_id: {{handle_id2}}}})
        RETURN collect(ID(r))
        """.format(rel_type=rel_type)
    else:
        q = """
            MATCH (a:Node {handle_id: {handle_id1}})-[r]-(b:Node {handle_id: {handle_id2}})
            RETURN collect(ID(r))
            """
    with manager.read as r:
        return r.execute(q, handle_id1=handle_id1, handle_id2=handle_id2).fetchall()[0][0]


def update_node_properties(manager, handle_id, new_properties):
    old_properties = get_node(manager, handle_id)
    d = {
        'props': update_item_properties(old_properties, new_properties)
    }
    q = """
        MATCH (n:Node {handle_id: {props}.handle_id})
        SET n = {props}
        RETURN n
        """
    with manager.transaction as w:
        return w.execute(q, **d).fetchall()[0][0]


def update_relationship_properties(manager, relationship_id, new_properties):
    old_properties = get_relationship(manager, relationship_id)
    d = {
        'props': update_item_properties(old_properties, new_properties)
    }
    q = """
        START r=relationship({relationship_id})
        SET r = {props}
        RETURN r
        """
    with manager.transaction as w:
        return w.execute(q, relationship_id=relationship_id, **d).fetchall()[0][0]
