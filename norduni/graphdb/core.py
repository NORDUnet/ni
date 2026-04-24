# -*- coding: utf-8 -*-
#
#       core.py
#
#       Copyright 2016 Johan Lundberg <lundberg@nordu.net>
#

# This started as an extension to the Neo4j REST client made by Versae, continued
# as an extension for the official Neo4j python bindings when they were released
# (Neo4j 1.5, python-embedded).
#
# After the release of neo4j 3.0 and the bolt protocol we replaced neo4jdb-python with
# the official Neo4j driver.
#
# The goal is to make it easier to add and retrieve data from a Neo4j database
# according to the NORDUnet Network Inventory data model.
#
# More information about NORDUnet Network Inventory:
# https://portal.nordu.net/display/NI/

from neo4j.v1 import GraphDatabase, basic_auth
from neo4j.exceptions import ProtocolError, ClientError
from . import exceptions
from . import models

import logging
logger = logging.getLogger(__name__)

# Load Django settings
NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD = None, None, None
MAX_POOL_SIZE = 50
ENCRYPTED = False
try:
    from django.conf import settings as django_settings
    try:
        # Mandatory Django settings for quick init
        NEO4J_URI = django_settings.NEO4J_RESOURCE_URI
        NEO4J_USERNAME = django_settings.NEO4J_USERNAME
        NEO4J_PASSWORD = django_settings.NEO4J_PASSWORD
    except AttributeError:
        pass
    # Optional Django settings for quick init
    try:
        MAX_POOL_SIZE = django_settings.NEO4J_MAX_POOL_SIZE
    except AttributeError:
        pass
    try:
        ENCRYPTED = django_settings.NEO4J_ENCRYPTED
    except AttributeError:
        pass
except ImportError:
    logger.info('Starting up without a Django environment.')
    logger.info('Initial: graphdb.neo4jdb == None.')
    logger.info('Use graphdb.init_db to open a database connection.')


META_TYPES = ['Physical', 'Logical', 'Relation', 'Location']


class GraphDB(object):

    _instance = None
    _manager = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._manager = self.manager

    @property
    def manager(self):
        if self._manager is None:
            try:
                self._manager = init_db()
            except Exception as e:
                logger.error('Could not create manager: {}'.format(e))
                self._manager = None
        return self._manager

    @manager.setter
    def manager(self, manager):
        self._manager = manager


def init_db(uri=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD, encrypted=ENCRYPTED,
            max_pool_size=MAX_POOL_SIZE):
    if uri:
        try:
            from .contextmanager import Neo4jDBSessionManager
            manager = Neo4jDBSessionManager(uri=uri, username=username, password=password, encrypted=encrypted,
                                            max_pool_size=max_pool_size)
            try:
                with manager.session as s:
                    s.run('CREATE CONSTRAINT ON (n:Node) ASSERT n.handle_id IS UNIQUE')
            except ClientError as e:
                if e.title == 'EquivalentSchemaRuleAlreadyExists':
                    logger.info('Unique constraint already exists')
                else:
                    raise e
            except Exception as e:
                logger.error('Could not create constraints for Neo4j database: {!s}'.format(uri))
                raise e
            try:
                create_index(manager, 'name')
            except ClientError as e:
                if e.title == 'EquivalentSchemaRuleAlreadyExists':
                    logger.info('Index already exists')
                else:
                    logger.error('Could not create index for Neo4j database: {!s}'.format(uri))
                    raise e
            except Exception as e:
                logger.error('Could not create index for Neo4j database: {!s}'.format(uri))
                raise e
            return manager
        except ProtocolError as e:
            logger.warning('Could not connect to Neo4j database: {!s}'.format(uri))
            raise e


def get_db_driver(uri, username=None, password=None, encrypted=True, max_pool_size=50, trust=0):
    """
    :param uri: Bolt uri
    :type uri: str
    :param username: Neo4j username
    :type username: str
    :param password: Neo4j password
    :type password: str
    :param encrypted: Use TLS
    :type encrypted: Boolean
    :param max_pool_size: Maximum number of idle sessions
    :type max_pool_size: Integer
    :param trust: Trust cert on first use (0) or do not accept unknown cert (1)
    :type trust: Integer
    :return: Neo4j driver
    :rtype: neo4j.v1.session.Driver
    """
    return GraphDatabase.driver(uri, auth=basic_auth(username, password), encrypted=encrypted,
                                max_pool_size=max_pool_size, trust=trust)


def query_to_dict(manager, query, **kwargs):
    d = {}
    with manager.session as s:
        result = s.run(query, kwargs)
        for record in result:
            for key, value in record.items():
                d[key] = value
    return d


def query_to_list(manager, query, **kwargs):
    out = []
    with manager.session as s:
        result = s.run(query, kwargs)
        for record in result:
            d = {}
            for key, value in record.items():
                d[key] = value
            out.append(d)
    return out


def query_to_iterator(manager, query, **kwargs):
    with manager.session as s:
        result = s.run(query, kwargs)
        for record in result:
            d = {}
            for key, value in record.items():
                d[key] = value
            yield d


def neo4j_entity_to_dict(node):
    return {k: v for k, v in node.items()}


def create_node(manager, name, meta_type_label, type_label, handle_id):
    """
    Creates a node with the mandatory attributes name and handle_id also sets type label.

    :param manager: Manager to handle sessions and transactions
    :param name: Node name
    :param meta_type_label: Node meta type
    :param type_label: Node label
    :param handle_id: Unique id

    :type manager: graphdb.contextmanager.Neo4jDBSessionManager
    :type name: str|unicode
    :type meta_type_label: str|unicode
    :type type_label: str|unicode
    :type handle_id: str|unicode

    :rtype: dict
    """
    if meta_type_label not in META_TYPES:
        raise exceptions.MetaLabelNamingError(meta_type_label)
    q = """
        CREATE (n:Node:%s:%s { name: $name, handle_id: $handle_id})
        RETURN n
        """ % (meta_type_label, type_label)
    with manager.session as s:
        return neo4j_entity_to_dict(s.run(q, {'name': name, 'handle_id': handle_id}).single()['n'])


def get_node(manager, handle_id):
    """
    :param manager: Manager to handle sessions and transactions
    :param handle_id: Unique id

    :type manager: graphdb.contextmanager.Neo4jDBSessionManager
    :type handle_id: str|unicode

    :rtype: dict|neo4j.v1.types.Node
    """
    q = 'MATCH (n:Node { handle_id: $handle_id }) RETURN n'

    with manager.session as s:
        result = s.run(q, {'handle_id': handle_id}).single()
        if result:
            return neo4j_entity_to_dict(result['n'])
    raise exceptions.NodeNotFound(manager, handle_id)


def get_node_bundle(manager, handle_id=None, node=None):
    """
    :param manager: Neo4jDBSessionManager
    :param handle_id: Unique id
    :type handle_id: str|unicode
    :param node: Node object
    :type node: neo4j.v1.types.Node
    :return: dict
    """
    if not node:
        q = 'MATCH (n:Node { handle_id: $handle_id }) RETURN n'
        with manager.session as s:
            result = s.run(q, {'handle_id': handle_id}).single()
            if not result:
                raise exceptions.NodeNotFound(manager, handle_id)
            node = result['n']
    d = {
        'data': neo4j_entity_to_dict(node)
    }
    labels = list(node.labels)
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

    :param manager: Neo4jDBSessionManager
    :param handle_id: Unique id

    :rtype: bool
    """
    q = """
        MATCH (n:Node {handle_id: $handle_id})
        OPTIONAL MATCH (n)-[r]-()
        DELETE n,r
        """
    with manager.session as s:
        s.run(q, {'handle_id': handle_id})
    return True


def get_relationship(manager, relationship_id):
    """
    :param manager: Manager to handle sessions and transactions
    :param relationship_id: Unique id

    :type manager: graphdb.contextmanager.Neo4jDBSessionManager
    :type relationship_id: int

    :rtype int|neo4j.v1.types.Relationship
    """
    q = """
        MATCH ()-[r]->()
        WHERE ID(r) = $relationship_id
        RETURN r
        """
    with manager.session as s:
        record = s.run(q, {'relationship_id': int(relationship_id)}).single()
        if record:
            return neo4j_entity_to_dict(record['r'])
    raise exceptions.RelationshipNotFound(manager, int(relationship_id))


def get_relationship_bundle(manager, relationship_id=None):
    """
    :param manager: Neo4jDBSessionManager
    :param relationship_id: Internal Neo4j id

    :type relationship_id: int

    :rtype: dictionary
    """
    q = """
        MATCH (start)-[r]->(end)
        WHERE ID(r) = $relationship_id
        RETURN start, r, end
        """

    with manager.session as s:
        record = s.run(q, {'relationship_id': int(relationship_id)}).single()
    if record is None:
        raise exceptions.RelationshipNotFound(manager, int(relationship_id))

    return {
        'type': record['r'].type,
        'id': int(relationship_id),
        'data': neo4j_entity_to_dict(record['r']),
        'start': neo4j_entity_to_dict(record['start']),
        'end': neo4j_entity_to_dict(record['end']),
    }


def delete_relationship(manager, relationship_id):
    """
    Deletes the relationship.

    :param manager:  Neo4jDBSessionManager
    :param relationship_id: Internal Neo4j relationship id
    :return: bool
    """
    q = """
        MATCH ()-[r]->()
        WHERE ID(r) = $relationship_id
        DELETE r
        """
    with manager.session as s:
        s.run(q, {'relationship_id': int(relationship_id)})
    return True


def get_node_meta_type(manager, handle_id):
    """
    Returns the meta type of the supplied node as a string.

    :param manager: Neo4jDBSessionManager
    :param handle_id: Unique id
    :return: string
    """
    node = get_node_bundle(manager=manager, handle_id=handle_id)
    if 'meta_type' not in node:
        raise exceptions.NoMetaLabelFound(handle_id)
    return node['meta_type']


# TODO: Try out elasticsearch
def get_nodes_by_value(manager, value, prop, node_type='Node'):
    """
    Traverses all nodes or nodes of specified label and compares the property/properties of the node
    with the supplied string.

    :param manager: Neo4jDBSessionManager
    :param value: Value to search for
    :param prop: Which property to look for value in
    :param node_type:

    :type value: str|list|bool|int
    :type prop: str
    :type node_type: str
    :return: dicts
    """
    q = """
        MATCH (n:{label})
        WHERE n.{prop} = $value
        RETURN distinct n
        """.format(label=node_type, prop=prop)

    with manager.session as s:
        for result in s.run(q, {'value': value}):
            yield neo4j_entity_to_dict(result['n'])


def get_node_by_type(manager, node_type):
    q = """
        MATCH (n:{label})
        RETURN distinct n
        """.format(label=node_type)
    with manager.session as s:
        for result in s.run(q):
            yield neo4j_entity_to_dict(result['n'])


def search_nodes_by_value(manager, value, prop=None, node_type='Node'):
    """
    Traverses all nodes or nodes of specified label and fuzzy compares the property/properties of the node
    with the supplied string.

    :param manager: Neo4jDBSessionManager
    :param value: Value to search for
    :param prop: Which property to look for value in
    :param node_type:

    :type value: str
    :type prop: str
    :type node_type: str
    :return: dicts
    """
    if prop:
        q = """
            MATCH (n:{label})
            WHERE n.{prop} =~ "(?i).*{value}.*" OR any(x IN n.{prop} WHERE x =~ "(?i).*{value}.*")
            RETURN distinct n
            """.format(label=node_type, prop=prop, value=value)
    else:
        q = """
            MATCH (n:{label})
            WITH n, keys(n) as props
            WHERE any(prop in props WHERE n[prop] =~ "(?i).*{value}.*") OR
              any(prop in props WHERE any(x IN n[prop] WHERE x =~ "(?i).*{value}.*"))
            RETURN distinct n
            """.format(label=node_type, value=value)

    with manager.session as s:
        for result in s.run(q):
            yield result['n']


# TODO: Try out elasticsearch
def get_nodes_by_type(manager, node_type):
    q = """
        MATCH (n:{label})
        RETURN n
        """.format(label=node_type)
    with manager.session as s:
        for result in s.run(q):
            yield result['n']


# TODO: Try out elasticsearch
def get_nodes_by_name(manager, name):
    q = """
        MATCH (n:Node {name: $name})
        RETURN n
        """
    with manager.session as s:
        for result in s.run(q, {'name': name}):
            yield result['n']


def create_index(manager, prop, node_type='Node'):
    """
    :param manager: Neo4jDBSessionManager
    :param prop: Property to index
    :param node_type: Label to create index on

    :type manager: Neo4jDBSessionManager
    :type prop: str
    :type node_type: str
    """
    with manager.session as s:
        s.run('CREATE INDEX ON :{node_type}({prop})'.format(node_type=node_type, prop=prop))


def get_indexed_node(manager, prop, value, node_type='Node', lookup_func='CONTAINS'):
    """
    :param manager: Neo4jDBSessionManager
    :param prop: Indexed property
    :param value: Indexed value
    :param node_type: Label used for index
    :param lookup_func: STARTS WITH | CONTAINS | ENDS WITH

    :type manager: Neo4jDBSessionManager
    :type prop: str
    :type value: str
    :type node_type: str
    :type lookup_func: str

    :return: Dict or Node object
    :rtype: dict|Node
    """
    q = """
        MATCH (n:{label})
        WHERE toLower(n.{prop}) {lookup_func} toLower($value)
        RETURN n
        """.format(label=node_type, prop=prop, lookup_func=lookup_func)
    with manager.session as s:
        for result in s.run(q, {'value': value}):
            yield neo4j_entity_to_dict(result['n'])


def get_unique_node_by_name(manager, node_name, node_type):
    """
    Returns the node if the node is unique for name and type or None.

    :param manager: Neo4jDBSessionManager
    :param node_name: string
    :param node_type: str|unicode
    :return: graphdb node model or None
    """
    q = """
        MATCH (n:Node { name: $name })
        WHERE $label IN labels(n)
        RETURN n.handle_id as handle_id
        """

    with manager.session as s:
        result = list(s.run(q, {'name': node_name, 'label': node_type}))

    if result:
        if len(result) == 1:
            return get_node_model(manager, result[0]['handle_id'])
        raise exceptions.MultipleNodesReturned(node_name, node_type)
    return None


def _create_relationship(manager, handle_id, other_handle_id, rel_type):
    q = """
        MATCH (a:Node {handle_id: $start}),(b:Node {handle_id: $end})
        CREATE (a)-[r:%s]->(b)
        RETURN r
        """ % rel_type

    with manager.session as s:
        return s.run(q, {'start': handle_id, 'end': other_handle_id}).single()['r'].id


def create_location_relationship(manager, location_handle_id, other_handle_id, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is raised.
    """
    other_meta_type = get_node_meta_type(manager, other_handle_id)
    if other_meta_type == 'Location' and rel_type == 'Has':
        return _create_relationship(manager, location_handle_id, other_handle_id, rel_type)
    raise exceptions.NoRelationshipPossible(location_handle_id, 'Location', other_handle_id, other_meta_type, rel_type)


def create_logical_relationship(manager, logical_handle_id, other_handle_id, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is raised.
    """
    other_meta_type = get_node_meta_type(manager, other_handle_id)
    if rel_type == 'Depends_on':
        if other_meta_type == 'Logical' or other_meta_type == 'Physical':
            return _create_relationship(manager, logical_handle_id, other_handle_id, rel_type)
    elif rel_type == 'Part_of':
        if other_meta_type == 'Physical':
            return _create_relationship(manager, logical_handle_id, other_handle_id, rel_type)
    raise exceptions.NoRelationshipPossible(logical_handle_id, 'Logical', other_handle_id, other_meta_type, rel_type)


def create_relation_relationship(manager, relation_handle_id, other_handle_id, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is raised.
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
    raise exceptions.NoRelationshipPossible(relation_handle_id, 'Relation', other_handle_id, other_meta_type, rel_type)


def create_physical_relationship(manager, physical_handle_id, other_handle_id, rel_type):
    """
    Makes relationship between the two nodes and returns the relationship.
    If a relationship is not possible NoRelationshipPossible exception is raised.
    """
    other_meta_type = get_node_meta_type(manager, other_handle_id)
    if other_meta_type == 'Physical':
        if rel_type == 'Has' or rel_type == 'Connected_to':
            return _create_relationship(manager, physical_handle_id, other_handle_id, rel_type)
    elif other_meta_type == 'Location' and rel_type == 'Located_in':
        return _create_relationship(manager, physical_handle_id, other_handle_id, rel_type)
    raise exceptions.NoRelationshipPossible(physical_handle_id, 'Physical', other_handle_id, other_meta_type, rel_type)


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
    other_meta_type = get_node_meta_type(manager, other_handle_id)
    raise exceptions.NoRelationshipPossible(handle_id, meta_type, other_handle_id, other_meta_type, rel_type)


def get_relationships(manager, handle_id1, handle_id2, rel_type=None):
    """
    Takes a start and an end node with an optional relationship type.
    Returns the relationships between the nodes or an empty list.
    """
    if rel_type:
        q = """
        MATCH (a:Node {{handle_id: $handle_id1}})-[r:{rel_type}]-(b:Node {{handle_id: $handle_id2}})
        RETURN collect(r) as relationships
        """.format(rel_type=rel_type)
    else:
        q = """
            MATCH (a:Node {handle_id: $handle_id1})-[r]-(b:Node {handle_id: $handle_id2})
            RETURN collect(r) as relationships
            """
    with manager.session as s:
        return s.run(q, {'handle_id1': handle_id1, 'handle_id2': handle_id2}).single()['relationships']


def set_node_properties(manager, handle_id, new_properties):
    new_properties['handle_id'] = handle_id  # Make sure the handle_id can't be changed

    q = """
        MATCH (n:Node {handle_id: $props.handle_id})
        SET n = $props
        RETURN n
        """
    with manager.session as s:
        return neo4j_entity_to_dict(s.run(q, {'handle_id': handle_id, 'props': new_properties}).single()['n'])


def set_relationship_properties(manager, relationship_id, new_properties):

    q = """
        MATCH ()-[r]->()
        WHERE ID(r) = $relationship_id
        SET r = $props
        RETURN r
        """
    with manager.session as s:
        return s.run(q, {'relationship_id': int(relationship_id), 'props': new_properties}).single()


def get_node_model(manager, handle_id=None, node=None):
    """
    :param manager: Context manager to handle transactions
    :type manager: Neo4jDBSessionManager
    :param handle_id: Nodes handle id
    :type handle_id: str|unicode
    :param node: Node object
    :type node: neo4j.v1.types.Node
    :return: Node model
    :rtype: models.BaseNodeModel or sub class of models.BaseNodeModel
    """
    bundle = get_node_bundle(manager, handle_id, node)
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
    """
    :param manager: Context manager to handle transactions
    :type manager: Neo4jDBSessionManager
    :param relationship_id: Internal Neo4j relationship id
    :type relationship_id: int
    :return: Relationship model
    :rtype: models.BaseRelationshipModel
    """
    bundle = get_relationship_bundle(manager, relationship_id)
    return models.BaseRelationshipModel(manager).load(bundle)
