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
import re
from neo4j import contextmanager

from . import exceptions
from . import helpers
from . import models

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
        try:
            manager = _get_db_manager(uri)
            try:
                with manager.transaction as w:
                    w.execute('CREATE CONSTRAINT ON (n:Node) ASSERT n.handle_id IS UNIQUE').fetchall()
            except exceptions.IntegrityError:
                pass
            try:
                with manager.transaction as w:
                    w.execute('CREATE INDEX ON :Node(name)').fetchall()
            except exceptions.IntegrityError:
                pass
            return manager
        except exceptions.SocketError as e:
            print 'Could not connect to Neo4j database:'
            print e


def _get_db_manager(uri):
    return contextmanager.Neo4jDBConnectionManager(uri)


def query_to_dict(manager, query, **kwargs):
    d = {}
    with manager.read as r:
        cursor = r.execute(query, **kwargs)
        result = cursor.fetchall()
        if result:
            for desc, data in zip(cursor.description, result[0]):
                d[desc[0]] = data
    return d


def query_to_list(manager, query, **kwargs):
    l = []
    with manager.read as r:
        cursor = r.execute(query, **kwargs)
        for row in cursor.fetchall():
            d = {}
            for desc, data in zip(cursor.description, row):
                d[desc[0]] = data
            l.append(d)
    return l


def query_to_iterator(manager, query, **kwargs):
    with manager.read as r:
        cursor = r.execute(query, **kwargs)
        for row in cursor:
            d = {}
            for desc, data in zip(cursor.description, row):
                d[desc[0]] = data
            yield d


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
        raise exceptions.MetaLabelNamingError(meta_type_label)
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
        raise exceptions.NodeNotFound(manager, handle_id)


def get_node_bundle(manager, handle_id):
    """
    :param manager: Neo4jDBConnectionManager
    :param handle_id: Unique id
    :return: dict
    """
    q = 'MATCH (n:Node { handle_id: {handle_id} }) RETURN labels(n),n'
    try:
        with manager.read as r:
            labels, data = r.execute(q, handle_id=handle_id).fetchall()[0]
    except (IndexError, ValueError):
        raise exceptions.NodeNotFound(manager, handle_id)
    d = {
        'data': data
    }
    labels.remove('Node')  # All nodes have this label for indexing
    for label in labels:
        if label in META_TYPES:
            d['meta_type'] = label
            labels.remove(label)
    d['labels'] = labels
    return d


def delete_node(manager, handle_id):
    """
    Deletes the node and all its relationships.

    :param manager: Neo4jDBConnectionManager
    :param handle_id: Unique id
    :return: bool
    """
    q = """
        MATCH (n:Node {handle_id: {handle_id}})
        OPTIONAL MATCH (n)-[r]-()
        DELETE n,r
        """
    with manager.transaction as t:
        t.execute(q, handle_id=handle_id).fetchall()
    return True


def get_relationship(manager, relationship_id):
    """
     :param manager: Neo4jDBConnectionManager
    :param relationship_id: Internal Neo4j id (integer)
    :return: dict
    """
    q = 'START r=relationship({relationship_id}) RETURN r'
    try:
        with manager.read as r:
            return r.execute(q, relationship_id=relationship_id).fetchall()[0][0]
    except exceptions.InternalError:
        raise exceptions.RelationshipNotFound(manager, relationship_id)


def get_relationship_bundle(manager, relationship_id):
    """
    :param manager: Neo4jDBConnectionManager
    :param relationship_id: Internal Neo4j id (integer)
    :return: dictionary
    """
    q = """
        START r=relationship({relationship_id})
        RETURN  type(r), id(r), r, startNode(r).handle_id,endNode(r).handle_id
        """
    try:
        with manager.read as r:
            t, i, data, start, end = r.execute(q, relationship_id=relationship_id).fetchall()[0]
    except exceptions.InternalError:
        raise exceptions.RelationshipNotFound(manager, relationship_id)
    return {'type': t, 'id': i, 'data': data, 'start': start, 'end': end}


def delete_relationship(manager, relationship_id):
    """
    Deletes the relationship.

    :param manager:  Neo4jDBConnectionManager
    :param relationship_id: Internal Neo4j relationship id
    :return: bool
    """
    q = 'START r=relationship({relationship_id}) DELETE r'
    try:
        with manager.transaction as t:
            t.execute(q, relationship_id=relationship_id).fetchall()
    except exceptions.InternalError:
        raise exceptions.RelationshipNotFound(manager, relationship_id)
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
    raise exceptions.NoMetaLabelFound(handle_id)


# TODO: Try out elasticsearch
def get_nodes_by_value(manager, value, prop=None, node_type=None):
    """
    Traverses all nodes or nodes of specified label and compares the property/properties of the node
    with the supplied string.

    :param manager: Neo4jDBConnectionManager
    :param value: string
    :param prop: string
    :param node_type:
    :return: dicts
    """
    if not node_type:
        node_type = 'Node'
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
        except exceptions.ProgrammingError:  # Can't do regex on int. bool or lists
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


# TODO: Try out elasticsearch
def get_nodes_by_type(manager, node_type):
    q = '''
        MATCH (n:{label})
        RETURN n
        '''.format(label=node_type)
    with manager.read as r:
        for node, in r.execute(q):
            yield node


# TODO: Try out elasticsearch
def get_nodes_by_name(manager, name):
    q = '''
        MATCH (n:Node {name: {name}})
        RETURN n
        '''
    with manager.read as r:
        for node, in r.execute(q, name=name):
            yield node


def legacy_node_index_search(manager, lucene_query):
    """
    :param lucene_query: string
    :return: dict
    """
    q = """
        START n=node:node_auto_index({lucene_query})
        RETURN collect(n.handle_id) as result
        """
    return query_to_dict(manager, q, lucene_query=lucene_query)


def get_unique_node_by_name(manager, node_name, node_type):
    """
    Returns the node if the node is unique for name and type or None.

    :param manager:  Neo4jDBConnectionManager
    :param node_name: string
    :param node_type: string
    :return: norduniclient node model or None
    """
    q = '''
        MATCH (n:Node { name: {name} })
        WHERE {label} IN labels(n)
        RETURN n.handle_id
        '''
    with manager.read as r:
        hits = r.execute(q, name=node_name, label=node_type).fetchall()
    if hits:
        if len(hits) == 1:
            return get_node_model(manager, hits[0][0])
        raise exceptions.MultipleNodesReturned(node_name, node_type)
    return None


def _create_relationship(manager, handle_id, other_handle_id, rel_type):

    q = """
        MATCH (a:Node {handle_id: {start}}),(b:Node {handle_id: {end}})
        CREATE a-[r:%s]->b
        RETURN ID(r)
        """ % rel_type

    with manager.transaction as w:
        return w.execute(q, start=handle_id, end=other_handle_id).fetchall()[0][0]


def create_location_relationship(manager, location_handle_id, other_handle_id, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    """
    if get_node_meta_type(manager, other_handle_id) == 'Location' and rel_type == 'Has':
        return _create_relationship(manager, location_handle_id, other_handle_id, rel_type)
    raise exceptions.NoRelationshipPossible(manager, location_handle_id, other_handle_id, rel_type)


def create_logical_relationship(manager, logical_handle_id, other_handle_id, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    """
    other_meta_type = get_node_meta_type(manager, other_handle_id)
    if rel_type == 'Depends_on':
        if other_meta_type == 'Logical' or other_meta_type == 'Physical':
            return _create_relationship(manager, logical_handle_id, other_handle_id, rel_type)
    elif rel_type == 'Part_of':
        if other_meta_type == 'Physical':
            return _create_relationship(manager, logical_handle_id, other_handle_id, rel_type)
    raise exceptions.NoRelationshipPossible(manager, logical_handle_id, other_handle_id, rel_type)


def create_relation_relationship(manager, relation_handle_id, other_handle_id, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    """
    other_meta_type = get_node_meta_type(manager, other_handle_id)
    if other_meta_type == 'Logical':
        if rel_type in ['Uses', 'Provides']:
            return _create_relationship(manager, relation_handle_id, other_handle_id, rel_type)
    elif other_meta_type == 'Location' and rel_type == 'Responsible_for':
        return _create_relationship(manager, relation_handle_id, other_handle_id, rel_type)
    elif other_meta_type == 'Physical':
        if rel_type in ['Owns', 'Provides']:
            return _create_relationship(manager, relation_handle_id, other_handle_id, rel_type)
    raise exceptions.NoRelationshipPossible(manager, relation_handle_id, other_handle_id, rel_type)


def create_physical_relationship(manager, physical_handle_id, other_handle_id, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is
    raised.
    """
    other_meta_type = get_node_meta_type(manager, other_handle_id)
    if other_meta_type == 'Physical':
        if rel_type == 'Has' or rel_type == 'Connected_to':
            return _create_relationship(manager, physical_handle_id, other_handle_id, rel_type)
    elif other_meta_type == 'Location' and rel_type == 'Located_in':
        return _create_relationship(manager, physical_handle_id, other_handle_id, rel_type)
    raise exceptions.NoRelationshipPossible(manager, physical_handle_id, other_handle_id, rel_type)


def create_relationship(manager, handle_id, other_handle_id, rel_type):
    """
    Makes a relationship from node to other_node depending on which
    meta_type the nodes are. Returns the relationship or raises
    NoRelationshipPossible exception.
    """
    meta_type = get_node_meta_type(manager, handle_id)
    if meta_type == 'Location':
        return create_location_relationship(manager, handle_id, other_handle_id, rel_type)
    elif meta_type == 'Logical':
        return create_logical_relationship(manager, handle_id, other_handle_id, rel_type)
    elif meta_type == 'Relation':
        return create_relation_relationship(manager, handle_id, other_handle_id, rel_type)
    elif meta_type == 'Physical':
        return create_physical_relationship(manager, handle_id, other_handle_id, rel_type)
    raise exceptions.NoRelationshipPossible(manager, handle_id, other_handle_id, rel_type)


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


def set_node_properties(manager, handle_id, new_properties):
    new_properties['handle_id'] = handle_id
    d = {
        'props': new_properties
    }
    q = """
        MATCH (n:Node {handle_id: {props}.handle_id})
        SET n = {props}
        RETURN n
        """
    try:
        with manager.transaction as w:
            return w.execute(q, **d).fetchall()[0][0]
    except exceptions.ProgrammingError:
        raise exceptions.BadProperties(d['props'])


def set_relationship_properties(manager, relationship_id, new_properties):
    d = {
        'props': new_properties
    }
    q = """
        START r=relationship({relationship_id})
        SET r = {props}
        RETURN r
        """
    try:
        with manager.transaction as w:
            return w.execute(q, relationship_id=relationship_id, **d).fetchall()[0][0]
    except exceptions.ProgrammingError:
        raise exceptions.BadProperties(d['props'])


def get_node_model(manager, handle_id):
    bundle = get_node_bundle(manager, handle_id)
    for label in bundle.get('labels'):
        try:
            classname = '{meta_type}{base}Model'.format(meta_type=bundle.get('meta_type'), base=label).replace('_', '')
            return getattr(models, classname)(manager).load(bundle)
        except AttributeError:
            pass
    for label in bundle.get('labels'):
        try:
            classname = '{base}Model'.format(base=label).replace('_', '')
            return getattr(models, classname)(manager).load(bundle)
        except AttributeError:
            pass
    try:
        classname = '{base}Model'.format(base=bundle.get('meta_type'))
        return getattr(models, classname)(manager).load(bundle)
    except AttributeError:
        return models.BaseNodeModel(manager).load(bundle)


def get_relationship_model(manager, relationship_id):
    try:
        relationship_id = int(relationship_id)
    except ValueError:
        raise exceptions.RelationshipNotFound(manager, relationship_id)
    bundle = get_relationship_bundle(manager, relationship_id)
    return models.BaseRelationshipModel(manager).load(bundle)
